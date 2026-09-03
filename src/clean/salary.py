"""Chuan hoa luong tu chuoi tho ve khoang so (VND).

Cac dang gap trong thuc te:
    "Sign in to view salary", "Thoả thuận", "Negotiable"  -> khong cong bo
    "$1,000 - $2,000", "1,000 - 2,000 USD"                -> khoang USD
    "Tới 1,500 USD", "Up to $2,000"                       -> chi co tran
    "Trên 20 triệu", "From $1,500"                        -> chi co san
    "10 - 20 triệu", "15 triệu"                           -> VND
Ket qua tra ve: (min, max, currency, disclosed)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

MILLION = 1_000_000


def _strip_accents(text: str) -> str:
    text = text.replace("Đ", "D").replace("đ", "d")
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")


NEGOTIABLE_TOKENS = (
    "sign in to view salary",
    "thoa thuan",
    "negotiable",
    "canh tranh",
    "competitive",
    "you'll love it",
    "dang nhap",
)

NUM_RE = re.compile(r"\d[\d.,]*")


@dataclass(frozen=True)
class Salary:
    min_vnd: float | None
    max_vnd: float | None
    currency: str | None          # 'USD' | 'VND' | None
    disclosed: bool

    @property
    def mid_vnd(self) -> float | None:
        vals = [v for v in (self.min_vnd, self.max_vnd) if v is not None]
        return sum(vals) / len(vals) if vals else None


def _to_number(token: str) -> float | None:
    """'1,500' -> 1500 ; '1.500' -> 1500 ; '15.5' -> 15.5"""
    token = token.strip()
    if not token:
        return None
    # Neu co ca . va , : dau dung sau cung la thap phan
    if "," in token and "." in token:
        if token.rfind(",") > token.rfind("."):
            token = token.replace(".", "").replace(",", ".")
        else:
            token = token.replace(",", "")
    elif "," in token:
        # ',' theo sau boi dung 3 chu so -> dau phan cach nghin
        token = token.replace(",", "") if re.search(r",\d{3}\b", token) else token.replace(",", ".")
    elif "." in token:
        token = token.replace(".", "") if re.search(r"\.\d{3}\b", token) else token
    try:
        return float(token)
    except ValueError:
        return None


def parse_salary(raw: str | None, usd_to_vnd: float = 25_400) -> Salary:
    if not raw or not raw.strip():
        return Salary(None, None, None, False)

    text = _strip_accents(raw).lower().strip()

    if any(tok in text for tok in NEGOTIABLE_TOKENS):
        return Salary(None, None, None, False)

    # xac dinh don vi
    is_usd = "usd" in text or "$" in text
    is_vnd_million = bool(re.search(r"\b(tr|trieu|million|m)\b", text)) or "trieu" in text
    unit_factor = usd_to_vnd if is_usd else (MILLION if is_vnd_million else None)

    numbers = [n for n in (_to_number(t) for t in NUM_RE.findall(text)) if n is not None]
    numbers = [n for n in numbers if n > 0]
    if not numbers:
        return Salary(None, None, None, False)

    if unit_factor is None:
        # khong ro don vi: doan theo do lon (vd "20.000.000" hoac "20")
        biggest = max(numbers)
        unit_factor = 1.0 if biggest >= 1_000_000 else MILLION
        currency = "VND"
    else:
        currency = "USD" if is_usd else "VND"

    only_max = bool(re.search(r"\b(toi|den|up to|max|upto)\b", text))
    only_min = bool(re.search(r"\b(tren|tu|from|min|starting)\b", text))

    if len(numbers) >= 2 and not (only_max or only_min):
        lo, hi = min(numbers[:2]), max(numbers[:2])
        return Salary(lo * unit_factor, hi * unit_factor, currency, True)

    value = numbers[0] * unit_factor
    if only_max:
        return Salary(None, value, currency, True)
    if only_min:
        return Salary(value, None, currency, True)
    return Salary(value, value, currency, True)
