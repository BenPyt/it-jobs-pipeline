"""Ham tro giup boc tach HTML.

Nguyen tac: KHONG bam chat vao ten class CSS (web hay doi class, crawler se
chet am tham). Thay vao do neo vao cau truc ben vung hon:
  - dang URL cua tin (regex),
  - quan he cha - con (card la to tien gan nhat chua ca link tin va link cong ty),
  - noi dung van ban (regex tren text).
Ten class chi dung nhu goi y (selector uu tien), va luon co duong lui.
"""
from __future__ import annotations

import re
from typing import Callable, Iterable

from bs4 import BeautifulSoup, Tag


def soup_of(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:  # noqa: BLE001 - neu chua cai lxml thi dung parser mac dinh
        return BeautifulSoup(html, "html.parser")


def closest_ancestor(node: Tag, predicate: Callable[[Tag], bool], max_up: int = 8) -> Tag | None:
    """Leo len cay DOM tim to tien dau tien thoa `predicate`."""
    current = node
    for _ in range(max_up):
        current = current.parent
        if current is None or not isinstance(current, Tag):
            return None
        if predicate(current):
            return current
    return None


def text_of(node: Tag | None, sep: str = "\n") -> str:
    if node is None:
        return ""
    return re.sub(r"[ \t]+", " ", node.get_text(sep, strip=True)).strip()


def first_match(lines: Iterable[str], pattern: re.Pattern[str]) -> str | None:
    for line in lines:
        if pattern.search(line):
            return line.strip()
    return None


def pick_by_class(root: Tag, keywords: Iterable[str]) -> Tag | None:
    """Tim phan tu dau tien co class chua mot trong cac tu khoa (selector uu tien)."""
    for kw in keywords:
        found = root.select_one(f'[class*="{kw}"]')
        if found is not None:
            return found
    return None


def clean_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.split("\n") if ln.strip()]
