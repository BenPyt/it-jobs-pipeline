"""Test bo tach HTML bang fixture - chay duoc offline, khong can mang.

Fixture mo phong dung cau truc that cua ITviec (khao sat 03/09/2026):
link tieu de la URL tuyet doi, ky nang co ?click_source=Skill+tag,
nhom nghe la link khong co id so.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.crawl.base import RawJob
from src.crawl.itviec import ITviecScraper
from src.crawl.topcv import TopCVScraper

FIX = pathlib.Path(__file__).parent / "fixtures"


def _itviec():
    return ITviecScraper(client=None, cfg={"base_url": "https://itviec.com", "list_path": "/it-jobs"})


def _topcv():
    return TopCVScraper(client=None, cfg={"base_url": "https://www.topcv.vn", "list_path": "/x"})


def _list_jobs():
    return {j.source_job_id: j
            for j in _itviec().parse_list_page((FIX / "itviec_list.html").read_text(encoding="utf-8"))}


def test_bat_dung_so_tin_va_loai_rac():
    jobs = _list_jobs()
    assert set(jobs) == {"5154", "3903"}, (
        "Chi lay tin trong div.job-card; menu, khoi quang cao va the ky nang "
        "co so trong slug (iso-27001) deu khong duoc tinh"
    )


def test_link_tieu_de_tuyet_doi_van_boc_duoc():
    j = _list_jobs()["5154"]
    assert j.title == "Senior IT Business Analyst (Banking)"
    assert j.url == "https://itviec.com/it-jobs/senior-it-business-analyst-banking-gft-technologies-vietnam-5154"


def test_cong_ty_lay_the_co_chu_khong_lay_the_logo():
    jobs = _list_jobs()
    assert jobs["5154"].company == "GFT Technologies Vietnam"
    assert jobs["3903"].company == "ProtonX"


def test_ky_nang_chi_lay_the_skill_tag():
    j = _list_jobs()["5154"]
    assert j.skills_raw == ["Business Analysis", "SQL", "Agile", "ISO 27001"]
    assert "Business Analyst" not in j.skills_raw, "Nhom nghe khong phai ky nang"


def test_nhom_nghe_luu_rieng():
    assert _list_jobs()["5154"].extra["job_category"] == "Business Analyst"
    assert _list_jobs()["3903"].extra["job_category"] == "AI / Machine Learning Engineer"


def test_dia_diem_hinh_thuc_thoi_diem():
    j = _list_jobs()["5154"]
    assert j.work_arrangement_raw == "Hybrid"
    assert j.location_raw == "Ho Chi Minh - Ha Noi"
    assert "2 minutes ago" in (j.posted_raw or "")
    assert j.salary_raw == "Sign in to view salary"


def test_chi_tiet_khong_vo_ky_nang_cua_tin_khac():
    scraper = _itviec()
    job = RawJob(source="itviec", source_job_id="2546", url="https://itviec.com/it-jobs/x-2546")
    job = scraper.parse_detail_page((FIX / "itviec_detail.html").read_text(encoding="utf-8"), job)
    assert job.skills_raw == ["Data Engineer", "Power BI", "Oracle"]
    assert "Kafka" not in job.skills_raw, "Ky nang o muc 'More jobs for you' khong thuoc tin nay"
    assert "Job description" in job.description_raw


def test_topcv_truong_du_lieu():
    jobs = {j.source_job_id: j for j in _topcv().parse_list_page(
        (FIX / "topcv_list.html").read_text(encoding="utf-8"))}
    assert len(jobs) == 2
    j = jobs["2275972"]
    assert j.title == "Java Backend Developer"
    assert "Smartbooks" in j.company
    assert j.salary_raw == "Tới 1,500 USD"
    assert "Đà Nẵng" in j.location_raw
