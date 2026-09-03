"""Buoc 2 cua pipeline: RAW -> PROCESSED.

Nhan danh sach tin tho (dict tu RawJob), tra ve DataFrame da lam sach:
- chuan hoa luong / dia diem / ky nang / cap bac
- khu trung lap trong cung nguon va giua cac nguon
- kiem tra chat luong (bao nhieu % thieu truong nao)
"""
from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from typing import Any, Iterable

import pandas as pd

from .location import parse_arrangement, parse_locations, primary_location
from .salary import parse_salary
from .seniority import parse_seniority
from .skills import normalize_skills

log = logging.getLogger(__name__)

COLUMNS = [
    "job_key", "source", "source_job_id", "url", "title", "title_clean",
    "company", "company_key", "seniority", "location_primary", "locations",
    "work_arrangement", "salary_raw", "salary_min_vnd", "salary_max_vnd",
    "salary_mid_vnd", "salary_currency", "salary_disclosed",
    "skills", "n_skills", "posted_raw", "description_raw", "crawled_at",
]


def _fold(text: str) -> str:
    text = (text or "").replace("Đ", "D").replace("đ", "d")
    nfkd = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", stripped.lower()).strip()


def _clean_title(title: str | None) -> str | None:
    if not title:
        return None
    # bo phan trong ngoac va cac ky tu trang thua: "Senior Dev (Java, Spring)" -> "Senior Dev"
    t = re.sub(r"\s*[\(\[].*?[\)\]]\s*", " ", title)
    t = re.sub(r"\s+", " ", t).strip(" -–—|,")
    return t or title.strip()


def _job_key(source: str, source_job_id: str) -> str:
    return f"{source}:{source_job_id}"


def _content_key(title: str | None, company: str | None) -> str:
    """Khoa noi dung de phat hien 1 tin dang tren nhieu nguon."""
    base = f"{_fold(_clean_title(title) or '')}|{_fold(company or '')}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def clean_jobs(raw_jobs: Iterable[dict[str, Any]], usd_to_vnd: float = 25_400) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for raw in raw_jobs:
        title = (raw.get("title") or "").strip() or None
        if not title:
            continue

        salary = parse_salary(raw.get("salary_raw"), usd_to_vnd=usd_to_vnd)
        locations = parse_locations(raw.get("location_raw"))
        skills = normalize_skills(raw.get("skills_raw"))

        rows.append(
            {
                "job_key": _job_key(raw["source"], raw["source_job_id"]),
                "source": raw["source"],
                "source_job_id": str(raw["source_job_id"]),
                "url": raw.get("url"),
                "title": title,
                "title_clean": _clean_title(title),
                "company": (raw.get("company") or "").strip() or None,
                "company_key": _fold(raw.get("company") or ""),
                "seniority": parse_seniority(title),
                "location_primary": primary_location(raw.get("location_raw")),
                "locations": locations,
                "work_arrangement": parse_arrangement(
                    raw.get("work_arrangement_raw"), raw.get("location_raw")
                ),
                "salary_raw": raw.get("salary_raw"),
                "salary_min_vnd": salary.min_vnd,
                "salary_max_vnd": salary.max_vnd,
                "salary_mid_vnd": salary.mid_vnd,
                "salary_currency": salary.currency,
                "salary_disclosed": salary.disclosed,
                "skills": skills,
                "n_skills": len(skills),
                "posted_raw": raw.get("posted_raw"),
                "description_raw": raw.get("description_raw"),
                "crawled_at": raw.get("crawled_at"),
                "_content_key": _content_key(title, raw.get("company")),
            }
        )

    df = pd.DataFrame(rows, columns=COLUMNS + ["_content_key"])
    if df.empty:
        return df.drop(columns=["_content_key"])

    before = len(df)
    # 1) trung lap trong cung nguon: giu ban crawl moi nhat
    df = df.sort_values("crawled_at").drop_duplicates("job_key", keep="last")
    # 2) trung lap giua cac nguon: gop lai thay vi vut bo (xem _merge_group)
    df = (
        df.groupby("_content_key", sort=False, group_keys=False)
        .apply(_merge_group, include_groups=False)
        .reset_index(drop=True)
    )
    log.info("Khu trung lap: %d -> %d tin", before, len(df))

    cols = [c for c in COLUMNS if c in df.columns] + ["sources", "n_sources"]
    return df[cols].reset_index(drop=True)


def _merge_group(group: pd.DataFrame) -> pd.DataFrame:
    """Gop cac tin trung nhau giua cac nguon thanh MOT ban day du nhat.

    Vi sao khong don gian giu ban dau tien: ITviec an luong con TopCV cong bo
    luong. Neu vut bo mot ban la mat du lieu. O day ta uu tien ban co luong,
    roi bu them cac truong con thieu tu cac ban con lai va hop nhat ky nang.
    """
    if len(group) == 1:
        row = group.copy()
        row["sources"] = [[row.iloc[0]["source"]]]
        row["n_sources"] = 1
        return row

    # ban tot nhat: co luong cong bo -> nhieu ky nang -> mo ta dai
    group = group.assign(_desc_len=group["description_raw"].fillna("").str.len())
    group = group.sort_values(
        ["salary_disclosed", "n_skills", "_desc_len"], ascending=False
    )
    best = group.iloc[[0]].copy()

    # bu cac o con trong bang gia tri dau tien khac null tu cac ban con lai
    for col in group.columns:
        if col in ("skills", "locations", "_desc_len"):
            continue
        if pd.isna(best.iloc[0][col]):
            candidates = group[col].dropna()
            if not candidates.empty:
                best.iloc[0, best.columns.get_loc(col)] = candidates.iloc[0]

    # hop nhat ky nang va dia diem tu moi nguon
    merged_skills: list[str] = []
    for lst in group["skills"]:
        for skill in lst or []:
            if skill not in merged_skills:
                merged_skills.append(skill)
    merged_locs: list[str] = []
    for lst in group["locations"]:
        for loc in lst or []:
            if loc not in merged_locs:
                merged_locs.append(loc)

    best.at[best.index[0], "skills"] = merged_skills
    best.at[best.index[0], "locations"] = merged_locs
    best.at[best.index[0], "n_skills"] = len(merged_skills)
    best["sources"] = [sorted(group["source"].unique().tolist())]
    best["n_sources"] = group["source"].nunique()
    return best.drop(columns=["_desc_len"])


def quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Bao cao ty le thieu du lieu tung cot - de biet pipeline dang yeu cho nao."""
    if df.empty:
        return pd.DataFrame(columns=["column", "missing", "missing_pct"])
    total = len(df)
    rows = []
    for col in df.columns:
        if col in ("skills", "locations"):
            missing = int(df[col].apply(lambda v: not v).sum())
        else:
            missing = int(df[col].isna().sum())
        rows.append({"column": col, "missing": missing, "missing_pct": round(100 * missing / total, 1)})
    return pd.DataFrame(rows).sort_values("missing_pct", ascending=False).reset_index(drop=True)
