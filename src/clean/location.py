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
    (r"\b(ba ria|vung tau)\b", "Bà Rịa - Vũng Tàu"),
    (r"\b(bac ninh)\b", "Bắc Ninh"),
    (r"\b(bac giang)\b", "Bắc Giang"),
    (r"\b(hai duong)\b", "Hải Dương"),
    (r"\b(hung yen)\b", "Hưng Yên"),
    (r"\b(nam dinh)\b", "Nam Định"),
    (r"\b(thai binh)\b", "Thái Bình"),
    (r"\b(thai nguyen)\b", "Thái Nguyên"),
    (r"\b(vinh phuc)\b", "Vĩnh Phúc"),
    (r"\b(quang ninh|ha long)\b", "Quảng Ninh"),
    (r"\b(thanh hoa)\b", "Thanh Hóa"),
    (r"\b(nghe an|vinh)\b", "Nghệ An"),
    (r"\b(ha tinh)\b", "Hà Tĩnh"),
    (r"\b(quang binh)\b", "Quảng Bình"),
    (r"\b(quang tri)\b", "Quảng Trị"),
    (r"\b(hue|thua thien)\b", "Huế"),
    (r"\b(quang nam|hoi an)\b", "Quảng Nam"),
    (r"\b(quang ngai)\b", "Quảng Ngãi"),
    (r"\b(binh dinh|quy nhon)\b", "Bình Định"),
    (r"\b(phu yen)\b", "Phú Yên"),
    (r"\b(nha trang|khanh hoa)\b", "Khánh Hòa"),
    (r"\b(ninh thuan)\b", "Ninh Thuận"),
    (r"\b(binh thuan|phan thiet)\b", "Bình Thuận"),
    (r"\b(lam dong|da lat)\b", "Lâm Đồng"),
    (r"\b(dak lak|buon ma thuot)\b", "Đắk Lắk"),
    (r"\b(gia lai|pleiku)\b", "Gia Lai"),
    (r"\b(kon tum)\b", "Kon Tum"),
    (r"\b(tay ninh)\b", "Tây Ninh"),
    (r"\b(long an)\b", "Long An"),
    (r"\b(tien giang)\b", "Tiền Giang"),
    (r"\b(ben tre)\b", "Bến Tre"),
    (r"\b(dong thap)\b", "Đồng Tháp"),
    (r"\b(vinh long)\b", "Vĩnh Long"),
    (r"\b(an giang|long xuyen)\b", "An Giang"),
    (r"\b(kien giang|phu quoc|rach gia)\b", "Kiên Giang"),
    (r"\b(ca mau)\b", "Cà Mau"),
    (r"\b(soc trang)\b", "Sóc Trăng"),
    (r"\b(bac lieu)\b", "Bạc Liêu"),
    (r"\b(tra vinh)\b", "Trà Vinh"),
    (r"\b(hau giang)\b", "Hậu Giang"),
    (r"\b(binh phuoc)\b", "Bình Phước"),
    (r"\b(lao cai|sa pa)\b", "Lào Cai"),
    (r"\b(nuoc ngoai|oversea|abroad)\b", "Nước ngoài"),
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
