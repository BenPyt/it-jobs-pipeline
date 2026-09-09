"""Xuat mot ban chup du lieu tu SQLite ra CSV de dashboard cong khai doc duoc.

Vi sao can buoc nay: Streamlit Community Cloud chay truc tiep tu GitHub, ma
thu muc data/ khong duoc dua len repo (dung luong + du lieu crawl). Neu khong
co gi thay the, dashboard deploy len se trong tron.

Giai phap: xuat mot ban chup nhe (chi cac cot dashboard can, bo mo ta dai) vao
data/snapshot/ - thu muc duy nhat trong data/ duoc phep len Git. Kem theo
meta.json ghi ro thoi diem chup va nguon, de nguoi xem biet ho dang nhin du
lieu cua ngay nao chu khong tuong la du lieu thoi gian thuc.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config, resolve  # noqa: E402
from src.store import JobStore  # noqa: E402

SNAPSHOT_DIR = ROOT / "data" / "snapshot"
# Bo description_raw: chiem phan lon dung luong ma dashboard khong dung toi
COLUMNS = [
    "job_key", "source", "url", "title", "title_clean", "company", "seniority",
    "location_primary", "work_arrangement", "salary_raw", "salary_min_vnd",
    "salary_max_vnd", "salary_mid_vnd", "salary_currency", "salary_disclosed",
    "n_skills", "posted_raw", "first_seen_at", "last_seen_at", "skills", "locations",
]


def main() -> int:
    cfg = load_config()
    store = JobStore(resolve(cfg.paths.db_path))
    try:
        df = store.load_jobs()
        runs = store.load_runs(limit=90)
    finally:
        store.close()

    if df.empty:
        print("CSDL rong - chua co gi de xuat.")
        return 1

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = df[[c for c in COLUMNS if c in df.columns]].copy()
    out["skills"] = out["skills"].apply(lambda v: ", ".join(v) if isinstance(v, list) else "")
    out["locations"] = out["locations"].apply(lambda v: ", ".join(v) if isinstance(v, list) else "")

    csv_path = SNAPSHOT_DIR / "jobs_snapshot.csv"
    out.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # Lich su cac lan chay: nguon du lieu cho tab "Suc khoe" khi dashboard
    # chay tren Streamlit Cloud (o do khong co CSDL SQLite).
    runs.to_csv(SNAPSHOT_DIR / "runs_snapshot.csv", index=False, encoding="utf-8-sig")

    meta = {
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_jobs": int(len(out)),
        "n_companies": int(out["company"].nunique()),
        "sources": out["source"].value_counts().to_dict(),
        "n_salary_disclosed": int(out["salary_disclosed"].sum()),
    }
    (SNAPSHOT_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    size_kb = csv_path.stat().st_size / 1024
    print(f"Da xuat {len(out)} tin -> {csv_path} ({size_kb:.0f} KB)")
    print(f"Meta: {meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
