"""Scraper cho ITviec (itviec.com).

Cau truc that cua trang danh sach (khao sat tu snapshot HTML ngay 03/09/2026):

    <div class="job-card" data-job-key="1a35488b-...">
        <a class="text-it-black" href="https://itviec.com/it-jobs/<slug>-5154">Tieu de</a>
        <a href="/companies/gft-technologies-vietnam">GFT Technologies Vietnam</a>
        <a class="sign-in-view-salary" href="/sign_in?job=...">Sign in to view salary</a>
        <a href="/it-jobs/business-analyst">Business Analyst</a>        <- nhom nghe
        <a href="/it-jobs/sql?click_source=Skill+tag">SQL</a>          <- ky nang
        ... text: "Posted 2 minutes ago | Hybrid | Ho Chi Minh - Ha Noi"
    </div>

Ba diem then chot rut ra tu khao sat:
1. Link tieu de la URL TUYET DOI (https://itviec.com/...), khong phai duong dan
   tuong doi -> selector kieu a[href^="/it-jobs/"] se bo sot toan bo tin.
2. Ky nang luon co tham so ?click_source=Skill+tag -> neo cuc ky ro rang,
   khong con phai doan xem link nao la ky nang, link nao la tin.
3. Nhom nghe (Business Analyst, Data Engineer...) la link /it-jobs/<slug>
   KHONG co id so o cuoi -> phan biet duoc voi link tin that.

Luong bi an sau dang nhap ("Sign in to view salary") o phan lon tin - day la
gioi han cua nguon nay, khong phai loi cua parser.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from .base import BaseScraper, RawJob
from .dom_utils import clean_lines, closest_ancestor, soup_of, text_of

# id so nam o cuoi slug: .../senior-it-business-analyst-...-vietnam-5154
JOB_ID_RE = re.compile(r"-(\d{3,6})(?:[/?#]|$)")
JOB_PATH_RE = re.compile(r"^/it-jobs/[^/?#]+$")
SKILL_TAG_SELECTOR = 'a[href*="click_source=Skill+tag"]'

LOCATION_RE = re.compile(
    r"\b(Ho Chi Minh|Ha Noi|Da Nang|Hai Phong|Can Tho|Binh Duong|Dong Nai|Hue|Nha Trang|Others)\b",
    re.IGNORECASE,
)
SALARY_RE = re.compile(
    r"(\$\s?[\d,.]+|\d[\d.,]*\s*(USD|VND|tr|trieu|million)|Sign in to view salary)", re.IGNORECASE
)
ARRANGEMENT_RE = re.compile(r"\b(At office|Hybrid|Remote|On-?site)\b", re.IGNORECASE)
POSTED_RE = re.compile(r"\d+\s+(second|minute|hour|day|week|month)s?\s+ago", re.IGNORECASE)


class ITviecScraper(BaseScraper):
    name = "itviec"

    # ---------- nhan dien URL ----------
    def job_id_from_url(self, url: str) -> str | None:
        path = urlparse(url).path
        if not JOB_PATH_RE.match(path) or "click_source" in url:
            return None
        m = JOB_ID_RE.search(path)
        return m.group(1) if m else None

    def list_page_url(self, page: int) -> str:
        path = self.cfg.get("list_path", "/it-jobs")
        return f"{self.base_url}{path}" if page == 1 else f"{self.base_url}{path}?page={page}"

    # ---------- trang danh sach ----------
    def parse_list_page(self, html: str) -> list[RawJob]:
        soup = soup_of(html)

        cards = soup.select("div.job-card")
        if not cards:
            # Duong lui: neu ITviec doi ten class, dung lai cach cu - tim link tin
            # roi leo len to tien chua ca link cong ty.
            self.log.warning("Khong thay div.job-card, dung co che du phong theo cau truc DOM")
            cards = self._fallback_cards(soup)

        jobs: dict[str, RawJob] = {}
        for card in cards:
            job = self._parse_card(card)
            if job is not None and job.source_job_id not in jobs:
                jobs[job.source_job_id] = job
        return list(jobs.values())

    def _fallback_cards(self, soup) -> list:
        cards, seen = [], set()
        for a in soup.select('a[href*="/it-jobs/"]'):
            if self.job_id_from_url(a.get("href", "")) is None:
                continue
            card = closest_ancestor(
                a, lambda t: t.select_one('a[href*="/companies/"]') is not None, max_up=8
            )
            if card is not None and id(card) not in seen:
                seen.add(id(card))
                cards.append(card)
        return cards

    def _parse_card(self, card) -> RawJob | None:
        # --- link tin: bo qua ky nang (Skill+tag) va nhom nghe (khong co id so) ---
        title_a = None
        for a in card.select('a[href*="/it-jobs/"]'):
            href = a.get("href", "")
            if "click_source" in href:
                continue
            if self.job_id_from_url(href) or JOB_ID_RE.search(urlparse(href).path):
                title_a = a
                break
        if title_a is None:
            return None

        href = title_a.get("href", "")
        url = urljoin(self.base_url + "/", href).split("?")[0]

        # id tin: uu tien so cuoi slug; neu khong co thi dung UUID cua the card
        job_id = self.job_id_from_url(url) or card.get("data-job-key")
        if not job_id:
            return None

        title = text_of(title_a, sep=" ").strip()
        if not title:
            return None

        # --- cong ty: the <a> dau tien tro toi /companies/ MA co chu ---
        company = None
        for a in card.select('a[href*="/companies/"]'):
            t = text_of(a, sep=" ").strip()
            if t:
                company = t
                break

        # --- ky nang: neo vao tham so click_source=Skill+tag ---
        skills: list[str] = []
        for a in card.select(SKILL_TAG_SELECTOR):
            label = text_of(a, sep=" ").strip()
            if label and label not in skills:
                skills.append(label)

        # --- nhom nghe: link /it-jobs/<slug> khong co id so ---
        category = None
        for a in card.select('a[href*="/it-jobs/"]'):
            h = a.get("href", "")
            if "click_source" in h or JOB_ID_RE.search(urlparse(h).path):
                continue
            category = text_of(a, sep=" ").strip() or None
            if category:
                break

        # --- luong ---
        salary_node = card.select_one("a.sign-in-view-salary, [class*='salary']")
        salary = text_of(salary_node, sep=" ").strip() or None

        # --- dia diem / hinh thuc / thoi diem dang: doc tu van ban con lai ---
        known = {title, company, salary, category}
        location = arrangement = posted = None
        for line in clean_lines(text_of(card)):
            if line in known or len(line) > 60:
                continue
            if arrangement is None and (m := ARRANGEMENT_RE.fullmatch(line.strip())):
                arrangement = m.group(1)
                continue
            if location is None and LOCATION_RE.search(line):
                location = line
                continue
            if posted is None and POSTED_RE.search(line):
                posted = line
            if salary is None and SALARY_RE.search(line):
                salary = line

        return RawJob(
            source=self.name,
            source_job_id=str(job_id),
            url=url,
            title=title,
            company=company,
            location_raw=location,
            salary_raw=salary,
            work_arrangement_raw=arrangement,
            posted_raw=posted,
            skills_raw=skills,
            extra={"job_category": category} if category else {},
        )

    # ---------- trang chi tiet ----------
    def parse_detail_page(self, html: str, job: RawJob) -> RawJob:
        soup = soup_of(html)

        # Ky nang cua CHINH tin nay nam TRUOC tieu de <h2> dau tien; moi the
        # Skill+tag phia sau thuoc muc "More jobs for you" o cuoi trang.
        first_h2 = soup.find("h2")
        order = {id(el): i for i, el in enumerate(soup.find_all(True))}
        limit = order.get(id(first_h2), 10**9) if first_h2 else 10**9
        own_skills: list[str] = []
        for a in soup.select(SKILL_TAG_SELECTOR):
            if order.get(id(a), 0) >= limit:
                break
            label = text_of(a, sep=" ").strip()
            if label and label not in own_skills:
                own_skills.append(label)
        if len(own_skills) > len(job.skills_raw):
            job.skills_raw = own_skills

        # Mo ta: cac khoi div.paragraph (Top 3 reasons / Job description / ...)
        paragraphs = soup.select("div.paragraph")
        if paragraphs:
            job.description_raw = "\n\n".join(text_of(p) for p in paragraphs)[:20000]

        # Cac truong con thieu thi bu them, KHONG ghi de cai da co tu trang danh sach
        lines = clean_lines(text_of(soup.select_one("main") or soup))
        for line in lines[:120]:
            if job.salary_raw is None and SALARY_RE.search(line) and len(line) < 60:
                job.salary_raw = line
            if job.location_raw is None and LOCATION_RE.search(line) and len(line) < 60:
                job.location_raw = line
            if job.work_arrangement_raw is None and (m := ARRANGEMENT_RE.fullmatch(line.strip())):
                job.work_arrangement_raw = m.group(1)
            if job.posted_raw is None and POSTED_RE.search(line) and len(line) < 60:
                job.posted_raw = line
        return job
