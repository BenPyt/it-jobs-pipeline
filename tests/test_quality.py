"""Test bo quy tac kiem tra chat luong du lieu."""
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.quality import FAILED, OK, WARNING, check_quality


def _df(n=50, source="careerlink", missing_company=0):
    rows = []
    for i in range(n):
        rows.append({
            "source": source, "title": f"Developer {i}",
            "url": f"https://x/{i}", "company": None if i < missing_company else f"Cty {i}",
            "location_primary": "Hồ Chí Minh", "salary_disclosed": i % 2 == 0,
        })
    return pd.DataFrame(rows)


def test_du_lieu_tot_thi_khong_canh_bao():
    rep = check_quality(_df())
    assert rep.status == OK and rep.issues == []


def test_khong_co_du_lieu_la_loi_nghiem_trong():
    rep = check_quality(pd.DataFrame())
    assert rep.status == FAILED
    assert rep.issues[0].check == "no_data"


def test_nguon_bien_mat_bi_bat():
    """Nguon khai bao trong config nhung khong tra ve tin nao."""
    rep = check_quality(_df(source="careerlink"), expected_sources=["careerlink", "itviec"])
    assert rep.status == FAILED
    assert any(i.check == "source_missing" and "itviec" in i.message for i in rep.issues)


def test_qua_it_tin_thi_canh_bao():
    rep = check_quality(_df(n=5))
    assert rep.status == WARNING
    assert rep.issues[0].check == "few_jobs"


def test_thieu_cot_quan_trong():
    rep = check_quality(_df(n=100, missing_company=40))   # thieu 40% > nguong 15%
    assert any(i.check == "missing_data" for i in rep.issues)


def test_tut_giam_dot_ngot_so_voi_lan_truoc():
    """Kich ban parser gay: hom qua 122 tin, hom nay con 5."""
    rep = check_quality(_df(n=5), previous={"careerlink": 122})
    assert rep.status == FAILED
    drop = [i for i in rep.issues if i.check == "sudden_drop"]
    assert drop and "122 -> 5" in drop[0].message


def test_giam_nhe_thi_khong_bao_dong():
    """Thi truong it viec hon mot chut la binh thuong, khong phai loi."""
    rep = check_quality(_df(n=100), previous={"careerlink": 120})
    assert not any(i.check == "sudden_drop" for i in rep.issues)


def test_bao_cao_chuyen_duoc_sang_json():
    rep = check_quality(_df(n=5), previous={"careerlink": 122})
    d = rep.to_dict()
    assert d["status"] == FAILED and d["per_source"] == {"careerlink": 5}
    assert isinstance(d["issues"], list) and d["issues"][0]["level"] in (WARNING, FAILED)
