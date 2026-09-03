"""Sinh du lieu MO PHONG de test pipeline & xem thu dashboard khi chua crawl duoc.

CANH BAO: day KHONG phai du lieu that. File sinh ra co tien to SAMPLE_ va
khong duoc dung de rut ra ket luan ve thi truong.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)
ROOT = Path(__file__).resolve().parents[1]

ROLES = [
    ("Data Engineer", ["Python", "SQL", "Airflow", "Spark", "Kafka", "AWS"]),
    ("Data Analyst", ["SQL", "Power BI", "Excel", "Python", "Tableau"]),
    ("Data Scientist", ["Python", "Machine Learning", "SQL", "Deep Learning"]),
    ("Backend Developer", ["Java", "Spring", "MySQL", "Docker", "REST API"]),
    ("Frontend Developer", ["JavaScript", "React", "TypeScript", "Vue.js"]),
    ("Fullstack Developer", ["Node.js", "React", "MongoDB", "TypeScript"]),
    ("DevOps Engineer", ["Docker", "Kubernetes", "AWS", "Terraform", "CI/CD"]),
    ("QA Engineer", ["QA/QC", "Selenium", "Python", "Agile/Scrum"]),
    ("Business Analyst", ["Business Analyst", "SQL", "Agile/Scrum", "English"]),
    ("AI Engineer", ["Python", "Deep Learning", "Computer Vision", "NLP"]),
]
LEVELS = ["Intern", "Fresher", "Junior", "Middle", "Senior", "Lead", "Manager", ""]
LEVEL_W = [3, 6, 14, 20, 30, 10, 5, 12]
COMPANIES = [
    "FPT Software", "VNG Corporation", "MoMo", "Tiki", "VNPAY", "Viettel Digital",
    "Techcombank", "Shopee Vietnam", "KMS Technology", "NashTech", "Axon",
    "Zalo", "One Mount Group", "Sun Asterisk", "Grab Vietnam",
]
LOCATIONS = ["Ho Chi Minh", "Ha Noi", "Da Nang", "Ho Chi Minh - Hybrid", "Ha Noi - Remote", "Binh Duong"]
LOC_W = [45, 33, 8, 6, 5, 3]


def salary_text(level: str, source: str) -> str:
    if source == "itviec" and random.random() < 0.75:
        return "Sign in to view salary"
    if random.random() < 0.35:
        return "Thoả thuận"
    base = {"Intern": 6, "Fresher": 10, "Junior": 16, "Middle": 26, "Senior": 40,
            "Lead": 55, "Manager": 70, "": 24}[level]
    lo = max(5, int(random.gauss(base, base * 0.18)))
    hi = int(lo * random.uniform(1.2, 1.6))
    style = random.random()
    if style < 0.55:
        return f"{lo} - {hi} triệu"
    if style < 0.8:
        return f"${int(lo*1_000_000/25_400)} - ${int(hi*1_000_000/25_400)}"
    return f"Tới {hi} triệu"


def build(n: int = 140) -> list[dict]:
    jobs, now = [], datetime.now(timezone.utc)
    for i in range(n):
        role, skills = random.choice(ROLES)
        level = random.choices(LEVELS, weights=LEVEL_W)[0]
        source = random.choices(["itviec", "topcv"], weights=[55, 45])[0]
        title = f"{level} {role}".strip()
        chosen = random.sample(skills, k=random.randint(2, min(5, len(skills))))
        jobs.append({
            "source": source,
            "source_job_id": f"{1000+i}",
            "url": f"https://example.invalid/{source}/{1000+i}",
            "title": title,
            "company": random.choice(COMPANIES),
            "location_raw": random.choices(LOCATIONS, weights=LOC_W)[0],
            "salary_raw": salary_text(level, source),
            "work_arrangement_raw": random.choice(["At office", "Hybrid", "Remote", None]),
            "posted_raw": f"Posted {random.randint(1, 20)} days ago",
            "skills_raw": chosen,
            "description_raw": f"[DU LIEU MO PHONG] Mo ta cong viec cho vi tri {title}.",
            "crawled_at": (now - timedelta(minutes=random.randint(0, 60))).isoformat(timespec="seconds"),
            "extra": {"synthetic": True},
        })
    return jobs


if __name__ == "__main__":
    out = ROOT / "data" / "raw" / "SAMPLE_jobs_demo.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = build()
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Da sinh {len(data)} tin MO PHONG -> {out}")
