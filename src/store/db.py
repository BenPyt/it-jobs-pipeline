"""Lop luu tru SQLite.

Diem quan trong: ghi PHAI idempotent - chay pipeline 10 lan tren cung du lieu
thi CSDL van chi co 1 ban ghi/tin, chi cap nhat last_seen_at. Nho vay co the
chay lai bat cu luc nao ma khong so nhan ban du lieu.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        """Them cot moi vao CSDL da ton tai.

        CREATE TABLE IF NOT EXISTS khong dung cho bang da co san - no bo qua
        luon, nen cot moi se khong bao gio duoc them. Day la buoc chuyen doi
        toi thieu de CSDL cu van dung duoc voi phien ban code moi.
        """
        existing = {r["name"] for r in self.conn.execute("PRAGMA table_info(crawl_runs)")}
        for col, ddl in (("quality", "TEXT"), ("n_issues", "INTEGER DEFAULT 0")):
            if col not in existing:
                self.conn.execute(f"ALTER TABLE crawl_runs ADD COLUMN {col} {ddl}")
                log.info("Da them cot crawl_runs.%s", col)

    # ---- theo doi cac lan chay ----
    def start_run(self, sources: list[str]) -> int:
        cur = self.conn.execute(
            "INSERT INTO crawl_runs (started_at, sources) VALUES (?, ?)",
            (_now(), ",".join(sources)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_run(self, run_id: int, n_raw: int, n_clean: int, status: str = "success",
                   note: str = "", quality: dict | None = None) -> None:
        self.conn.execute(
            "UPDATE crawl_runs SET finished_at=?, n_raw=?, n_clean=?, status=?, note=?, "
            "quality=?, n_issues=? WHERE run_id=?",
            (_now(), n_raw, n_clean, status, note,
             json.dumps(quality, ensure_ascii=False) if quality else None,
             len((quality or {}).get("issues", [])), run_id),
        )
        self.conn.commit()

    def previous_source_counts(self, before_run_id: int) -> dict[str, int]:
        """So tin theo nguon cua lan chay THANH CONG gan nhat truoc do.

        Dung lam moc so sanh: hom nay thu duoc it hon han hom qua la dau hieu
        parser bi gay chu khong phai thi truong bong dung it viec.
        """
        row = self.conn.execute(
            "SELECT quality FROM crawl_runs WHERE run_id < ? AND quality IS NOT NULL "
            "AND status != 'failed' ORDER BY run_id DESC LIMIT 1",
            (before_run_id,),
        ).fetchone()
        if not row or not row["quality"]:
            return {}
        try:
            return json.loads(row["quality"]).get("per_source", {})
        except json.JSONDecodeError:
            return {}

    def load_runs(self, limit: int = 60) -> pd.DataFrame:
        """Lich su cac lan chay - nguon du lieu cho tab suc khoe cua dashboard."""
        df = pd.read_sql_query(
            "SELECT run_id, started_at, finished_at, sources, n_raw, n_clean, status, "
            "note, n_issues, quality FROM crawl_runs ORDER BY run_id DESC LIMIT ?",
            self.conn, params=(limit,),
        )
        return df

    # ---- ghi du lieu ----
    def _skill_id(self, name: str) -> int:
        self.conn.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (name,))
        row = self.conn.execute("SELECT skill_id FROM skills WHERE name=?", (name,)).fetchone()
        return int(row["skill_id"])

    def upsert_jobs(self, df: pd.DataFrame, run_id: int | None = None) -> tuple[int, int]:
        """Tra ve (so tin moi, so tin cap nhat)."""
        if df.empty:
            return 0, 0

        now = _now()
        inserted = updated = 0

        for _, row in df.iterrows():
            key = row["job_key"]
            exists = self.conn.execute(
                "SELECT 1 FROM jobs WHERE job_key=?", (key,)
            ).fetchone() is not None

            values = {
                "job_key": key,
                "source": row["source"],
                "source_job_id": str(row["source_job_id"]),
                "url": row.get("url"),
                "title": row["title"],
                "title_clean": row.get("title_clean"),
                "company": row.get("company"),
                "company_key": row.get("company_key"),
                "seniority": row.get("seniority"),
                "location_primary": row.get("location_primary"),
                "work_arrangement": row.get("work_arrangement"),
                "salary_raw": row.get("salary_raw"),
                "salary_min_vnd": _num(row.get("salary_min_vnd")),
                "salary_max_vnd": _num(row.get("salary_max_vnd")),
                "salary_mid_vnd": _num(row.get("salary_mid_vnd")),
                "salary_currency": row.get("salary_currency"),
                "salary_disclosed": int(bool(row.get("salary_disclosed"))),
                "n_skills": int(row.get("n_skills") or 0),
                "n_sources": int(row.get("n_sources") or 1),
                "sources": json.dumps(list(row.get("sources") or [row["source"]]), ensure_ascii=False),
                "posted_raw": row.get("posted_raw"),
                "description_raw": row.get("description_raw"),
                "last_seen_at": now,
                "run_id": run_id,
            }

            if exists:
                sets = ", ".join(f"{k}=:{k}" for k in values if k != "job_key")
                self.conn.execute(f"UPDATE jobs SET {sets} WHERE job_key=:job_key", values)
                updated += 1
            else:
                values["first_seen_at"] = now
                cols = ", ".join(values)
                placeholders = ", ".join(f":{k}" for k in values)
                self.conn.execute(f"INSERT INTO jobs ({cols}) VALUES ({placeholders})", values)
                inserted += 1

            # ghi lai quan he ky nang / dia diem (xoa cu -> ghi moi cho dung)
            self.conn.execute("DELETE FROM job_skills WHERE job_key=?", (key,))
            for skill in row.get("skills") or []:
                self.conn.execute(
                    "INSERT OR IGNORE INTO job_skills (job_key, skill_id) VALUES (?, ?)",
                    (key, self._skill_id(skill)),
                )
            self.conn.execute("DELETE FROM job_locations WHERE job_key=?", (key,))
            for loc in row.get("locations") or []:
                self.conn.execute(
                    "INSERT OR IGNORE INTO job_locations (job_key, location) VALUES (?, ?)",
                    (key, loc),
                )

        self.conn.commit()
        log.info("Ghi CSDL: %d tin moi, %d tin cap nhat", inserted, updated)
        return inserted, updated

    # ---- doc du lieu cho dashboard ----
    def load_jobs(self) -> pd.DataFrame:
        df = pd.read_sql_query("SELECT * FROM jobs", self.conn)
        if df.empty:
            return df
        skills = pd.read_sql_query(
            "SELECT js.job_key, s.name FROM job_skills js JOIN skills s USING (skill_id)", self.conn
        )
        mapping = skills.groupby("job_key")["name"].apply(list).to_dict()
        df["skills"] = df["job_key"].map(mapping).apply(lambda v: v if isinstance(v, list) else [])
        locs = pd.read_sql_query("SELECT job_key, location FROM job_locations", self.conn)
        lmap = locs.groupby("job_key")["location"].apply(list).to_dict()
        df["locations"] = df["job_key"].map(lmap).apply(lambda v: v if isinstance(v, list) else [])
        df["salary_disclosed"] = df["salary_disclosed"].astype(bool)
        return df

    def close(self) -> None:
        self.conn.close()


def _num(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
