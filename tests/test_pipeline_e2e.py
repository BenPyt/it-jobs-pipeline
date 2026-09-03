"""Test xuyen suot: lam sach -> ghi CSDL -> doc lai. Khong dung mang."""
import pathlib
import sys
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

from src.clean import clean_jobs
from src.store import JobStore

RAW = [
    dict(source="itviec", source_job_id="2130", url="https://itviec.com/a",
         title="Senior Data Engineer", company="SSI Securities Corporation",
         location_raw="Ha Noi - At office", salary_raw="Sign in to view salary",
         skills_raw=["ETL", "Kafka"], crawled_at="2026-09-03T07:00:00+00:00"),
    dict(source="topcv", source_job_id="9999", url="https://topcv.vn/b",
         title="Senior Data Engineer (Spark)", company="SSI Securities Corporation",
         location_raw="Hà Nội", salary_raw="30 - 50 triệu",
         skills_raw=["spark"], crawled_at="2026-09-03T07:00:00+00:00"),
    dict(source="topcv", source_job_id="2275972", url="https://topcv.vn/c",
         title="Java Backend Developer", company="Smartbooks",
         location_raw="Hà Nội & Đà Nẵng", salary_raw="Tới 1,500 USD",
         skills_raw=["Java", "Spring Boot"], crawled_at="2026-09-03T07:00:00+00:00"),
]


def test_gop_tin_trung_giua_hai_nguon():
    df = clean_jobs(RAW)
    assert len(df) == 2, "Hai tin cung title+company o 2 nguon phai gop lam mot"
    merged = df[df["n_sources"] == 2].iloc[0]
    # ban gop phai giu duoc luong cua TopCV va hinh thuc lam viec cua ITviec
    assert merged["salary_min_vnd"] == 30_000_000
    assert merged["work_arrangement"] == "At office"
    assert set(merged["skills"]) == {"Spark", "ETL", "Kafka"}


def test_ghi_csdl_idempotent(tmp_path):
    df = clean_jobs(RAW)
    store = JobStore(tmp_path / "test.db")
    try:
        run1 = store.start_run(["itviec", "topcv"])
        ins1, upd1 = store.upsert_jobs(df, run_id=run1)
        ins2, upd2 = store.upsert_jobs(df, run_id=run1)   # chay lai lan 2
        assert (ins1, upd1) == (2, 0)
        assert (ins2, upd2) == (0, 2), "Chay lai khong duoc tao ban ghi trung"

        back = store.load_jobs()
        assert len(back) == 2
        row = back[back["n_sources"] == 2].iloc[0]
        assert set(row["skills"]) == {"Spark", "ETL", "Kafka"}
        assert "Đà Nẵng" in back[back["source_job_id"] == "2275972"].iloc[0]["locations"]
    finally:
        store.close()
