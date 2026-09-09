"""Kiem tra chat luong du lieu sau moi lan chay pipeline.

Vi sao can: khi pipeline chay tay, ban doc log va thay ngay co gi sai. Khi no
chay theo lich hang ngay thi khong ai nhin - trang web doi giao dien, parser
tra ve 0 tin, pipeline van bao "thanh cong" va ghi du lieu rong vao CSDL.
Vai tuan sau moi phat hien thi da mat vai tuan du lieu.

Module nay bien nhung gia dinh ngam thanh QUY TAC TUONG MINH, kiem tra sau moi
lan chay, va bao dong khi vi pham. Ba nhom quy tac:

1. Nguong tuyet doi   - moi nguon phai thu duoc it nhat N tin
2. Ty le thieu du lieu - cot nao khong duoc thieu qua X%
3. So sanh voi lan truoc - so tin tut qua manh la dau hieu parser gay

Muc do: OK / WARNING (ghi nhan, van chay tiep) / FAILED (co van de nghiem trong).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

OK, WARNING, FAILED = "ok", "warning", "failed"
_RANK = {OK: 0, WARNING: 1, FAILED: 2}


@dataclass
class Issue:
    level: str          # warning | failed
    check: str          # ten quy tac bi vi pham
    message: str        # mo ta cho nguoi doc
    value: Any = None   # gia tri thuc te do duoc
    threshold: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level, "check": self.check, "message": self.message,
            "value": self.value, "threshold": self.threshold,
        }


@dataclass
class QualityReport:
    status: str = OK
    n_jobs: int = 0
    per_source: dict[str, int] = field(default_factory=dict)
    missing_pct: dict[str, float] = field(default_factory=dict)
    salary_disclosed_pct: float = 0.0
    issues: list[Issue] = field(default_factory=list)

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)
        if _RANK[issue.level] > _RANK[self.status]:
            self.status = issue.level

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "n_jobs": self.n_jobs,
            "per_source": self.per_source,
            "missing_pct": self.missing_pct,
            "salary_disclosed_pct": round(self.salary_disclosed_pct, 1),
            "issues": [i.to_dict() for i in self.issues],
        }

    def summary(self) -> str:
        if not self.issues:
            return f"Chat luong OK - {self.n_jobs} tin, khong co canh bao."
        lines = [f"Chat luong: {self.status.upper()} - {len(self.issues)} van de"]
        for i in self.issues:
            lines.append(f"  [{i.level}] {i.check}: {i.message}")
        return "\n".join(lines)


DEFAULT_RULES: dict[str, Any] = {
    "min_jobs_per_source": 20,
    "max_missing_pct": {"title": 0, "url": 0, "company": 15, "location_primary": 25},
    "max_drop_vs_previous_pct": 50,
    "min_salary_disclosed_pct": 0,      # 0 = khong kiem tra
}


def _missing_pct(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns or df.empty:
        return 100.0
    return round(100 * float(df[col].isna().mean()), 1)


def check_quality(
    df: pd.DataFrame,
    rules: dict[str, Any] | None = None,
    previous: dict[str, int] | None = None,
    expected_sources: list[str] | None = None,
) -> QualityReport:
    """Doi chieu du lieu vua lam sach voi bo quy tac.

    `previous` la so tin theo nguon cua lan chay truoc (de phat hien tut giam).
    `expected_sources` la cac nguon LE RA phai co - nho vay bat duoc ca truong
    hop mot nguon bien mat hoan toan, thu ma kiem tra tren df khong thay duoc.
    """
    rules = {**DEFAULT_RULES, **(rules or {})}
    rep = QualityReport(n_jobs=len(df))

    if df.empty:
        rep.add(Issue(FAILED, "no_data", "Khong co tin nao sau khi lam sach", 0, ">0"))
        return rep

    rep.per_source = df["source"].value_counts().to_dict()
    rep.salary_disclosed_pct = 100 * float(df["salary_disclosed"].mean())

    # 1. Nguong tuyet doi cho tung nguon
    min_jobs = rules["min_jobs_per_source"]
    for source in (expected_sources or list(rep.per_source)):
        n = rep.per_source.get(source, 0)
        if n == 0:
            rep.add(Issue(FAILED, "source_missing",
                          f"Nguon '{source}' khong thu duoc tin nao", 0, f">={min_jobs}"))
        elif n < min_jobs:
            rep.add(Issue(WARNING, "few_jobs",
                          f"Nguon '{source}' chi co {n} tin", n, f">={min_jobs}"))

    # 2. Ty le thieu du lieu tung cot
    for col, max_pct in rules["max_missing_pct"].items():
        pct = _missing_pct(df, col)
        rep.missing_pct[col] = pct
        if pct > max_pct:
            level = FAILED if col in ("title", "url") else WARNING
            rep.add(Issue(level, "missing_data",
                          f"Cot '{col}' thieu {pct}% (nguong {max_pct}%)", pct, max_pct))

    # 3. So sanh voi lan chay truoc
    max_drop = rules["max_drop_vs_previous_pct"]
    for source, prev_n in (previous or {}).items():
        now_n = rep.per_source.get(source, 0)
        if prev_n >= min_jobs and now_n < prev_n * (1 - max_drop / 100):
            drop = round(100 * (1 - now_n / prev_n))
            rep.add(Issue(FAILED, "sudden_drop",
                          f"Nguon '{source}' tut {drop}% so voi lan truoc "
                          f"({prev_n} -> {now_n}) - nghi parser bi gay",
                          now_n, f">={round(prev_n * (1 - max_drop / 100))}"))

    # 4. Ty le cong bo luong (tuy chon)
    min_sal = rules.get("min_salary_disclosed_pct", 0)
    if min_sal and rep.salary_disclosed_pct < min_sal:
        rep.add(Issue(WARNING, "low_salary_coverage",
                      f"Chi {rep.salary_disclosed_pct:.0f}% tin co luong",
                      round(rep.salary_disclosed_pct, 1), min_sal))

    return rep
