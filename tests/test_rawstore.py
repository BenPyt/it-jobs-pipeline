"""Test tang luu tru du lieu tho (JSONL)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.crawl.rawstore import RawWriter, iter_raw, read_raw


def test_ghi_tung_dong_va_doc_lai(tmp_path):
    path = tmp_path / "jobs.jsonl"
    with RawWriter(path) as w:
        w.write({"source": "itviec", "title": "Kỹ sư dữ liệu"})
        w.write({"source": "topcv", "title": "Lập trình viên"})
        assert w.count == 2
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
    records = read_raw(path)
    assert records[0]["title"] == "Kỹ sư dữ liệu", "Tieng Viet phai giu nguyen, khong bi \\uXXXX"


def test_du_lieu_con_nguyen_khi_ghi_do_dang(tmp_path):
    """Mo phong crash: ghi 2 dong xong roi file bi cat cut o dong thu 3."""
    path = tmp_path / "jobs.jsonl"
    with RawWriter(path) as w:
        w.write({"id": 1})
        w.write({"id": 2})
    with open(path, "a", encoding="utf-8") as fh:
        fh.write('{"id": 3, "title": "bi ngat giua')   # dong hong, khong xuong dong

    records = read_raw(path)
    assert [r["id"] for r in records] == [1, 2], "Dong hong bi bo qua, 2 dong truoc van doc duoc"


def test_tuong_thich_nguoc_voi_file_json_cu(tmp_path):
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps([{"id": 1}, {"id": 2}]), encoding="utf-8")
    assert len(read_raw(path)) == 2


def test_doc_lan_luot(tmp_path):
    path = tmp_path / "jobs.jsonl"
    with RawWriter(path) as w:
        for i in range(5):
            w.write({"id": i})
    assert [r["id"] for r in iter_raw(path)] == [0, 1, 2, 3, 4]


def test_ghi_them_khong_de_len_du_lieu_cu(tmp_path):
    path = tmp_path / "jobs.jsonl"
    with RawWriter(path) as w:
        w.write({"id": 1})
    with RawWriter(path) as w:          # mo lai lan 2
        w.write({"id": 2})
    assert [r["id"] for r in read_raw(path)] == [1, 2]
