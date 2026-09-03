"""Scraper cho TopCV (topcv.vn).

Dac diem nguon nay:
- URL tin dang /viec-lam/<slug>/<id>.html -> id nam san trong URL.
- Luong hien cong khai ("Tới 1,500 USD", "10 - 20 triệu", "Thoả thuận")
  -> day la nguon chinh cho phan tich luong.
"""
from __future__ import annotations

import re

from .base import BaseScraper, RawJob
from .dom_utils import clean_lines, closest_ancestor, pick_by_class, soup_of, text_of

JOB_URL_RE = re.compile(r"/viec-lam/[^/]+/(\d+)\.html")

SALARY_HINT_RE = re.compile(
    r"(thoả thuận|thỏa thuận|triệu|tr\b|USD|\$|trên|tới|đến)", re.IGNORECASE
)


class TopCVScraper(BaseScraper):
    name = "topcv"

    def job_id_from_url(self, url: str) -> str | None:
        m = JOB_URL_RE.search(url)
        return m.group(1) if m else None

    def list_page_url(self, page: int) -> str:
        path = self.cfg.get("list_path", "/tim-viec-lam-it-phan-mem-c10026")
        return f"{self.base_url}{path}" if page == 1 else f"{self.base_url}{path}?page={page}"

    def parse_list_page(self, html: str) -> list[RawJob]:
        soup = soup_of(html)
        jobs: dict[str, RawJob] = {}

        for anchor in soup.select('a[href*="/viec-lam/"]'):
            href = anchor.get("href", "")
            m = JOB_URL_RE.search(href)
            if not m:
                continue
            job_id = m.group(1)
            if job_id in jobs:
                continue

            title = text_of(anchor, sep=" ").strip()
            if not title or len(title) > 200:
                continue

            # card = to tien gan nhat chua ca link cong ty (/cong-ty/ hoac /brand/)
            card = closest_ancestor(
                anchor,
                lambda t: t.select_one('a[href*="/cong-ty/"], a[href*="/brand/"]') is not None,
                max_up=8,
            )

            company = location = salary = deadline = None
            if card is not None:
                company_a = card.select_one('a[href*="/cong-ty/"], a[href*="/brand/"]')
                company = text_of(company_a, sep=" ") or None

                # uu tien selector theo class (TopCV dat ten kha on dinh)
                sal_node = pick_by_class(card, ["title-salary", "salary"])
                salary = text_of(sal_node, sep=" ") or None
                loc_node = pick_by_class(card, ["address", "city"])
                location = text_of(loc_node, sep=" ") or None
                dl_node = pick_by_class(card, ["deadline", "time"])
                deadline = text_of(dl_node, sep=" ") or None

                # duong lui: neu class doi ten, do tim tren van ban cua card
                if salary is None:
                    for line in clean_lines(text_of(card)):
                        if SALARY_HINT_RE.search(line) and len(line) < 40:
                            salary = line
                            break

            jobs[job_id] = RawJob(
                source=self.name,
                source_job_id=job_id,
                url=href.split("?")[0] if href.startswith("http") else self.base_url + href.split("?")[0],
                title=title,
                company=company,
                location_raw=location,
                salary_raw=salary,
                posted_raw=deadline,
            )

        return list(jobs.values())

    def parse_detail_page(self, html: str, job: RawJob) -> RawJob:
        soup = soup_of(html)
        main = soup.select_one("main") or soup.body or soup
        lines = clean_lines(text_of(main))

        if not job.salary_raw:
            for line in lines[:60]:
                if SALARY_HINT_RE.search(line) and len(line) < 40:
                    job.salary_raw = line
                    break

        # TopCV liet ke ky nang o muc "Kỹ năng" / tag
        skills: list[str] = []
        for tag_a in main.select('a[href*="/tim-viec-lam-"], a[class*="tag"]'):
            label = text_of(tag_a, sep=" ")
            if label and 1 < len(label) <= 40 and label not in skills:
                skills.append(label)
        job.skills_raw = skills[:25]

        desc_node = pick_by_class(main, ["job-description", "job-data", "content"]) or main
        desc = text_of(desc_node)
        job.description_raw = desc[:20000] if desc else None
        return job
