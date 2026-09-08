"""Test parser CareerLink tren fixture lay tu HTML that (08/09/2026)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.crawl.careerlink import CareerLinkScraper, _looks_like_it_job

FIX = pathlib.Path(__file__).parent / "fixtures"


def _scraper(**cfg):
    base = {"base_url": "https://www.careerlink.vn", "list_path": "/viec-lam/k/X"}
    base.update(cfg)
    return CareerLinkScraper(client=None, cfg=base)


def _jobs(**cfg):
    html = (FIX / "careerlink_list.html").read_text(encoding="utf-8")
    return {j.source_job_id: j for j in _scraper(**cfg).parse_list_page(html)}


def test_loc_bo_tin_ngoai_nganh_it():
    jobs = _jobs()
    assert set(jobs) == {"3616418", "3616252"}, "Tin 'nhan vien kinh doanh' phai bi loai"


def test_tat_bo_loc_thi_lay_het():
    assert len(_jobs(it_only=False)) == 3


def test_truong_du_lieu_day_du():
    j = _jobs()["3616418"]
    assert j.title == "TRƯỞNG BỘ PHẬN HỆ THỐNG PHẦN MỀM & DỮ LIỆU"
    assert j.company == "Công Ty TNHH Thương Mại Dịch Vụ Âu Châu"
    assert j.salary_raw == "20 triệu - 22 triệu"
    assert j.location_raw == "Hồ Chí Minh"
    assert j.extra["career_level"] == "Trưởng nhóm / Giám sát"
    assert j.url == "https://www.careerlink.vn/tim-viec-lam/truong-bo-phan-he-thong-phan-mem-du-lieu/3616418"


def test_nhieu_dia_diem_gop_lai():
    assert _jobs()["3616252"].location_raw == "Đà Nẵng - Hà Nội"


def test_thoi_diem_cap_nhat_doc_tu_timestamp():
    """HTML tho chi co Unix timestamp; phan chu do JavaScript dien."""
    assert _jobs()["3616418"].posted_raw.startswith("2026-")


def test_luong_thoa_thuan_giu_nguyen_chuoi():
    assert _jobs()["3616252"].salary_raw == "Thương lượng"


def test_bo_loc_nganh():
    assert _looks_like_it_job("Back-end Developer")
    assert _looks_like_it_job("Kỹ sư phần mềm")
    assert not _looks_like_it_job("Nhân viên kinh doanh sản phẩm công nghệ")
    assert not _looks_like_it_job("Giáo viên Tiếng Anh")
