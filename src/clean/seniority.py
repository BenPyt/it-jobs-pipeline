"""Suy ra cap bac (seniority) tu tieu de tin tuyen dung."""
from __future__ import annotations

import re
import unicodedata


def _norm(text: str) -> str:
    text = text.replace("Đ", "D").replace("đ", "d")
    nfkd = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", stripped).lower()


# Thu tu QUAN TRONG: xet tu cap cao xuong thap de "senior manager" ra Manager,
# va de "intern" khong bi nuot boi "internal".
LEVEL_PATTERNS: list[tuple[str, str]] = [
    (r"\b(c-?level|cto|cio|head of|director|giam doc)\b", "Head/Director"),
    (r"\b(manager|truong phong|quan ly)\b", "Manager"),
    (r"\b(principal|staff engineer|architect|kien truc su)\b", "Principal/Architect"),
    (r"\b(team lead|tech lead|lead|leader|truong nhom)\b", "Lead"),
    (r"\b(senior|sr\.?|cao cap)\b", "Senior"),
    (r"\b(middle|mid-?level|mid)\b", "Middle"),
    (r"\b(junior|jr\.?)\b", "Junior"),
    (r"\b(fresher|entry|moi tot nghiep)\b", "Fresher"),
    (r"\b(intern|internship|thuc tap)\b", "Intern"),
]

ORDER = [
    "Intern", "Fresher", "Junior", "Middle", "Senior",
    "Lead", "Principal/Architect", "Manager", "Head/Director", "Không rõ",
]


def parse_seniority(title: str | None) -> str:
    if not title:
        return "Không rõ"
    text = _norm(title)
    for pattern, level in LEVEL_PATTERNS:
        if re.search(pattern, text):
            return level
    return "Không rõ"
