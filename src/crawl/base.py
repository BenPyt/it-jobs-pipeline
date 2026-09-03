"""Lop scraper truu tuong + kieu du lieu chung cho moi nguon tuyen dung.

Y tuong: moi trang web co cach hien thi khac nhau, nhung deu quy ve mot
"RawJob" giong nhau. Nho vay module clean/ va store/ khong can biet du lieu
den tu ITviec hay TopCV.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.parse import urlparse

log = logging.getLogger(__name__)


@dataclass
class RawJob:
    """Mot tin tuyen dung o dang tho, chua lam sach."""

    source: str                      # ten nguon: itviec / topcv
    source_job_id: str               # id tin tren nguon do (tach tu URL)
    url: str
    title: str | None = None
    company: str | None = None
    location_raw: str | None = None
    salary_raw: str | None = None
    work_arrangement_raw: str | None = None   # At office / Hybrid / Remote
    posted_raw: str | None = None             # "Posted 2 days ago", "Hom nay"
    skills_raw: list[str] = field(default_factory=list)
    description_raw: str | None = None
    crawled_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseScraper(ABC):
    """Khung chung: duyet trang danh sach -> (tuy chon) vao trang chi tiet."""

    name: str = "base"

    def __init__(self, client, cfg: dict) -> None:
        self.client = client
        self.cfg = cfg
        self.base_url: str = cfg["base_url"].rstrip("/")
        self.max_pages: int = int(cfg.get("max_pages", 1))
        self.fetch_detail: bool = bool(cfg.get("fetch_detail", False))
        self.max_details: int = int(cfg.get("max_details", 100))
        self.log = logging.getLogger(f"scraper.{self.name}")

    # --- moi nguon phai tu cai dat 3 ham duoi ---
    @abstractmethod
    def list_page_url(self, page: int) -> str:
        """Tra ve URL cua trang danh sach thu `page` (bat dau tu 1)."""

    @abstractmethod
    def parse_list_page(self, html: str) -> list[RawJob]:
        """Bóc tach cac tin tu HTML trang danh sach."""

    @abstractmethod
    def parse_detail_page(self, html: str, job: RawJob) -> RawJob:
        """Bo sung thong tin tu trang chi tiet vao `job`."""

    # --- nhan dien URL: dung khi doc lai tu snapshot HTML da luu ---
    def owns_url(self, url: str) -> bool:
        """URL nay co thuoc nguon cua scraper nay khong?"""
        host = urlparse(url).netloc.lower().removeprefix("www.")
        base_host = urlparse(self.base_url).netloc.lower().removeprefix("www.")
        return host == base_host

    def is_detail_url(self, url: str) -> bool:
        """URL nay la trang chi tiet mot tin, hay trang danh sach?"""
        return self.job_id_from_url(url) is not None

    def job_id_from_url(self, url: str) -> str | None:
        """Tach id tin tu URL. Tra ve None neu khong phai URL trang chi tiet."""
        return None

    # --- luong chay chung ---
    def scrape(self) -> Iterator[RawJob]:
        seen: set[str] = set()
        detail_count = 0

        for page in range(1, self.max_pages + 1):
            url = self.list_page_url(page)
            self.log.info("Doc trang danh sach %d: %s", page, url)
            try:
                html = self.client.get_html(url)
            except Exception as exc:  # noqa: BLE001
                self.log.error("Bo qua trang %d (%s)", page, exc)
                continue

            jobs = self.parse_list_page(html)
            self.log.info("  -> tim thay %d tin", len(jobs))
            if not jobs:
                self.log.warning("Trang %d khong co tin nao, dung som.", page)
                break

            for job in jobs:
                key = f"{job.source}:{job.source_job_id}"
                if key in seen:
                    continue
                seen.add(key)

                if self.fetch_detail and detail_count < self.max_details:
                    try:
                        detail_html = self.client.get_html(job.url)
                        job = self.parse_detail_page(detail_html, job)
                        detail_count += 1
                    except Exception as exc:  # noqa: BLE001
                        self.log.warning("Khong lay duoc chi tiet %s (%s)", job.url, exc)
                yield job
