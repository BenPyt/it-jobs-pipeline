#!/usr/bin/env python3
"""Diem chay chinh cua pipeline: CRAWL -> CLEAN -> STORE.

Vi du:
    python run_pipeline.py                        # chay day du theo config.yaml
    python run_pipeline.py --sources itviec       # chi crawl 1 nguon
    python run_pipeline.py --max-pages 2 --no-detail
    python run_pipeline.py --from-raw data/raw/jobs_20260903_120000.jsonl
                                                  # lam sach lai tu file raw da co
    python run_pipeline.py --from-html data/raw/html_20260903_142919
                                                  # boc tach lai tu HTML da luu
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from src.clean import clean_jobs, quality_report
from src.config import PROJECT_ROOT, load_config, resolve
from src.crawl import SCRAPERS, RawJob
from src.crawl.http import HttpClient
from src.crawl.rawstore import RawWriter, read_raw
from src.logging_setup import setup_logging
from src.store import JobStore

log = logging.getLogger("pipeline")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pipeline thu thap & lam sach tin tuyen dung IT")
    p.add_argument("--config", default=None, help="Duong dan config.yaml")
    p.add_argument("--sources", nargs="*", default=None, help="Chi chay cac nguon nay")
    p.add_argument("--max-pages", type=int, default=None, help="Ghi de so trang danh sach")
    p.add_argument("--no-detail", action="store_true", help="Bo qua buoc vao trang chi tiet")
    p.add_argument("--from-raw", default=None,
                   help="Bo qua crawl, lam sach lai tu file raw (.jsonl hoac .json)")
    p.add_argument("--from-html", default=None,
                   help="Bo qua crawl, boc tach lai tu thu muc snapshot HTML (data/raw/html_*)")
    return p.parse_args()


def do_crawl(cfg, args) -> tuple[list[dict], Path]:
    """Crawl tat ca nguon duoc bat, tra ve (danh sach tin tho, duong dan file raw)."""
    http_cfg = cfg.crawl.http
    raw_dir = resolve(cfg.paths.raw_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    client = HttpClient(
        user_agent=http_cfg["user_agent"],
        timeout=http_cfg["timeout"],
        max_retries=http_cfg["max_retries"],
        backoff_factor=http_cfg["backoff_factor"],
        delay_seconds=http_cfg["delay_seconds"],
        jitter=http_cfg["jitter"],
        snapshot_dir=raw_dir / f"html_{stamp}",
    )

    raw_path = raw_dir / f"jobs_{stamp}.jsonl"
    all_jobs: list[dict] = []

    for source_cfg in cfg.crawl["sources"]:
        name = source_cfg["name"]
        # Neu nguoi dung chi dinh --sources thi y muon tuong minh thang cau hinh
        if args.sources:
            if name not in args.sources:
                continue
        elif not source_cfg.get("enabled", True):
            continue
        if name not in SCRAPERS:
            log.warning("Chua co scraper cho nguon '%s', bo qua.", name)
            continue

        source_cfg = dict(source_cfg)
        if args.max_pages:
            source_cfg["max_pages"] = args.max_pages
        if args.no_detail:
            source_cfg["fetch_detail"] = False

        scraper = SCRAPERS[name](client, source_cfg)
        log.info("=== Bat dau crawl nguon: %s ===", name)
        count = 0
        # Ghi tung tin xuong dia NGAY khi lay duoc: mat mang o tin thu 900
        # thi 899 tin truoc do van con nguyen tren dia.
        with RawWriter(raw_path) as writer:
            for job in scraper.scrape():
                record = job.to_dict()
                writer.write(record)
                all_jobs.append(record)
                count += 1
        log.info("=== %s: thu duoc %d tin ===", name, count)

    log.info("Da luu du lieu tho: %s (%d tin)", raw_path, len(all_jobs))
    return all_jobs, raw_path


def do_reparse_html(cfg, args, html_dir: Path) -> tuple[list[dict], Path]:
    """Boc tach lai tu HTML da luu, KHONG cham vao mang.

    Dung khi parser bi sai: sua selector -> chay lai tren dung nhung trang
    da tai ve, so sanh ket qua truoc/sau. Khong lam phien server, khong lo
    trang web da doi noi dung giua hai lan thu.
    """
    index_path = html_dir / "_index.jsonl"
    if not index_path.exists():
        raise FileNotFoundError(
            f"Khong tim thay so muc {index_path}. Thu muc snapshot cu (truoc khi "
            "co _index.jsonl) khong dung duoc cho --from-html."
        )

    entries = read_raw(index_path)
    log.info("So muc snapshot: %d trang trong %s", len(entries), html_dir)

    scrapers = []
    for source_cfg in cfg.crawl["sources"]:
        name = source_cfg["name"]
        if name not in SCRAPERS:
            continue
        if args.sources:
            if name not in args.sources:
                continue
        elif not source_cfg.get("enabled", True):
            continue
        scrapers.append(SCRAPERS[name](client=None, cfg=dict(source_cfg)))

    jobs: dict[str, dict] = {}
    details: list[tuple] = []

    for entry in entries:
        url, fname = entry["url"], entry["file"]
        scraper = next((s for s in scrapers if s.owns_url(url)), None)
        if scraper is None:
            continue
        html = (html_dir / fname).read_text(encoding="utf-8")

        if scraper.is_detail_url(url):
            details.append((scraper, url, html))          # xu ly sau
        else:
            for job in scraper.parse_list_page(html):     # trang danh sach
                jobs.setdefault(f"{job.source}:{job.source_job_id}", job.to_dict())

    # trang chi tiet: bo sung vao tin da co (neu tin do khong con trong danh sach
    # thi dung chinh trang chi tiet de dung lai ban ghi toi thieu)
    for scraper, url, html in details:
        job_id = scraper.job_id_from_url(url)
        key = f"{scraper.name}:{job_id}"
        base = jobs.get(key)
        raw = RawJob(source=scraper.name, source_job_id=job_id, url=url) if base is None \
            else RawJob(**{k: v for k, v in base.items() if k in RawJob.__dataclass_fields__})
        jobs[key] = scraper.parse_detail_page(html, raw).to_dict()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = resolve(cfg.paths.raw_dir) / f"jobs_reparsed_{stamp}.jsonl"
    with RawWriter(raw_path) as writer:
        for record in jobs.values():
            writer.write(record)
    log.info("Boc tach lai xong: %d tin -> %s", len(jobs), raw_path)
    return list(jobs.values()), raw_path


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config)
    setup_logging(resolve(cfg.paths.log_dir))

    store = JobStore(resolve(cfg.paths.db_path))
    sources = args.sources or [s["name"] for s in cfg.crawl["sources"] if s.get("enabled", True)]
    run_id = store.start_run(sources)

    try:
        if args.from_raw:
            raw_jobs = read_raw(args.from_raw)
            log.info("Doc lai %d tin tho tu %s", len(raw_jobs), args.from_raw)
        elif args.from_html:
            raw_jobs, _ = do_reparse_html(cfg, args, Path(args.from_html))
        else:
            raw_jobs, _ = do_crawl(cfg, args)

        df = clean_jobs(raw_jobs, usd_to_vnd=cfg.clean["usd_to_vnd"])
        log.info("Sau khi lam sach: %d tin", len(df))

        processed_dir = resolve(cfg.paths.processed_dir)
        processed_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_csv = processed_dir / f"jobs_clean_{stamp}.csv"
        df.assign(
            skills=df["skills"].apply(lambda v: ", ".join(v)),
            locations=df["locations"].apply(lambda v: ", ".join(v)),
            sources=df["sources"].apply(lambda v: ", ".join(v)),
        ).to_csv(out_csv, index=False, encoding="utf-8-sig")
        log.info("Da luu du lieu sach: %s", out_csv)

        if not df.empty:
            log.info("Bao cao chat luong (top thieu du lieu):\n%s",
                     quality_report(df).head(8).to_string(index=False))

        inserted, updated = store.upsert_jobs(df, run_id=run_id)
        store.finish_run(run_id, n_raw=len(raw_jobs), n_clean=len(df),
                         note=f"moi={inserted}, cap_nhat={updated}")
        print(f"\nXong. Tin tho: {len(raw_jobs)} | Sau lam sach: {len(df)} | "
              f"Moi: {inserted} | Cap nhat: {updated}")
        print(f"CSDL: {resolve(cfg.paths.db_path)}")
        print("Chay dashboard: streamlit run dashboard/app.py")
        return 0
    except Exception as exc:  # noqa: BLE001
        log.exception("Pipeline that bai")
        store.finish_run(run_id, 0, 0, status="failed", note=str(exc)[:500])
        return 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
