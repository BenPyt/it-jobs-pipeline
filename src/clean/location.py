"""Chuan hoa dia diem lam viec ve ten thanh pho chuan.

Van de thuc te: cung mot noi nhung viet nhieu kieu — "Ho Chi Minh",
"Hồ Chí Minh", "TP.HCM", "HCM", "Ha Noi - Hybrid", "Hà Nội & Đà Nẵng (mới)".
"""
from __future__ import annotations

import re
import unicodedata


def _norm(text: str) -> str:
    # Luu y: "Đ"/"đ" la ky tu rieng trong Unicode, NFD KHONG tach duoc dau gach,
    # nen phai thay thu cong truoc khi bo dau (neu khong "Đà Nẵng" se khong khop).
    text = text.replace("Đ", "D").replace("đ", "d")
    nfkd = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", stripped).lower().strip()


# tu khoa (da bo dau) -> ten chuan
CITY_PATTERNS: list[tuple[str, str]] = [
    (r"\b(ho chi minh|hcm|tphcm|tp\.?\s?hcm|sai gon|saigon)\b", "Hồ Chí Minh"),
    (r"\b(ha noi|hanoi|hn)\b", "Hà Nội"),
    (r"\b(da nang|danang)\b", "Đà Nẵng"),
    (r"\b(hai phong)\b", "Hải Phòng"),
    (r"\b(can tho)\b", "Cần Thơ"),
    (r"\b(binh duong)\b", "Bình Dương"),
    (r"\b(dong nai)\b", "Đồng Nai"),
    (r"\b(bac ninh)\b", "Bắc Ninh"),
    (r"\b(hue|thua thien)\b", "Huế"),
    (r"\b(nha trang|khanh hoa)\b", "Khánh Hòa"),
    (r"\b(quang nam)\b", "Quảng Nam"),
    (r"\b(remote|toan quoc|all)\b", "Remote/Toàn quốc"),
]

ARRANGEMENT_PATTERNS: list[tuple[str, str]] = [
    (r"\b(hybrid)\b", "Hybrid"),
    (r"\b(remote|work from home|wfh)\b", "Remote"),
    (r"\b(at office|onsite|on-site|tai van phong)\b", "At office"),
]


def parse_locations(raw: str | None) -> list[str]:
    """Tra ve danh sach thanh pho chuan xuat hien trong chuoi."""
    if not raw:
        return []
    text = _norm(raw)
    found: list[str] = []
    for pattern, canonical in CITY_PATTERNS:
        if re.search(pattern, text) and canonical not in found:
            found.append(canonical)
    return found


def primary_location(raw: str | None) -> str | None:
    locs = parse_locations(raw)
    return locs[0] if locs else None


def parse_arrangement(*raws: str | None) -> str | None:
    """Doc hinh thuc lam viec tu mot hoac nhieu chuoi (dia diem, cot rieng...)."""
    for raw in raws:
        if not raw:
            continue
        text = _norm(raw)
        for pattern, canonical in ARRANGEMENT_PATTERNS:
            if re.search(pattern, text):
                return canonical
    return None
