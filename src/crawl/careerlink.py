"""Scraper cho CareerLink (careerlink.vn).

Vi sao chon nguon nay (khao sat 08/09/2026):
- robots.txt cho phep: khoi User-agent:* chi cam trang "nha tuyen dung hang dau"
  va payload noi bo /*_rsc=; trang tim viec hoan toan mo.
- Tra ve 200 voi header trinh duyet binh thuong (TopCV va JobsGO deu 403).
- LUONG CONG KHAI ngay tren trang danh sach ("20 trieu - 22 trieu") - day la
  ly do chinh, vi ITviec an luong gan nhu toan bo tin.
- 50 tin/trang, cau truc HTML on dinh va ro rang.

Cau truc mot the tin:
    <li class="list-group-item job-item ...">
        <a class="job-link" href="/tim-viec-lam/<slug>/3615393?source=site">Tieu de</a>
        <a class="job-company" href="/viec-lam-cua/<slug>/384392">Ten cong ty</a>
        <a href="/tim-viec-lam-tai/dong-nai/DNI">Dong Nai</a>      <- co the co nhieu
        <span class="job-salary">20 trieu - 22 trieu</span>
        <a class="job-position" href="...career_levels=P,M">Quan ly / Truong phong</a>
        <span class="cl-datetime" data-datetime="1788848319"></span>
    </li>

Luu y ve chat luong du lieu: trang danh sach duoc loc theo TU KHOA chu khong
phai theo nganh, nen lot vao ca tin ngoai nganh (kinh doanh, telesale...).
Bo loc _looks_like_it_job() chan chung ngay tu buoc boc tach.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urljoin

from .base import BaseScraper, RawJob
from .dom_utils import clean_lines, soup_of, text_of

# /tim-viec-lam/<slug>/3615393?source=site
JOB_URL_RE = re.compile(r"/tim-viec-lam/[^/]+/(\d+)")
POSTED_RE = re.compile(r"(Cập nhật|Đăng)\s*:?\s*(.+)", re.IGNORECASE)

# --- bo loc nganh IT ---
_IT_KEYWORDS = (
    "developer", " dev ", "lap trinh", "phan mem", "software", "engineer",
    " it ", "it ", " it", "cong nghe thong tin", "data", "du lieu", "devops",
    "tester", "qa", "qc", "system", "he thong", "network", "mang", "database",
    "co so du lieu", "web", "mobile", "android", "ios", "java", "python", "php",
    ".net", "dotnet", "frontend", "front-end", "backend", "back-end", "fullstack",
    "full-stack", "ai ", " ai", "machine learning", "cloud", "devsecops",
    "security", "an ninh mang", "helpdesk", "business analyst", "erp", "sap",
    "kiem thu", "quan tri mang", "technical", "ky thuat phan mem", "react",
    "angular", "nodejs", "golang", "flutter", "bi ", "power bi", "sql",
)
_NOT_IT_KEYWORDS = (
    "kinh doanh", "telesale", "ban hang", "sale ", " sale", "tu van vien",
    "giao vien", "lai xe", "tai xe", "giam sat ca", "store manager",
    "cua hang truong", "phuc vu", "le tan", "ke toan", "nhan su", "tuyen dung",
    "marketing", "content", "thu ngan", "cong nhan", "bao ve", "tap vu",
    "chu nhiem lop", "gia su", "duoc si", "dieu duong",
)


def _fold(text: str) -> str:
    text = (text or "").replace("Đ", "D").replace("đ", "d")
    nfkd = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", stripped).lower()


def _looks_like_it_job(title: str) -> bool:
    """Tin nay co thuoc nganh IT khong?

    Danh sach cam thang danh sach cho phep: "Nhan vien kinh doanh san pham
    cong nghe" co chua "cong nghe" nhung khong phai viec IT.
    """
    folded = f" {_fold(title)} "
    if any(kw in folded for kw in _NOT_IT_KEYWORDS):
        return False
    return any(kw in folded for kw in _IT_KEYWORDS)


class CareerLinkScraper(BaseScraper):
    name = "careerlink"

    def job_id_from_url(self, url: str) -> str | None:
        m = JOB_URL_RE.search(url)
        return m.group(1) if m else None

    def list_page_url(self, page: int) -> str:
        path = self.cfg.get("list_path", "/viec-lam/k/C%C3%B4ng-Ngh%E1%BB%87-Th%C3%B4ng-Tin")
        return f"{self.base_url}{path}" if page == 1 else f"{self.base_url}{path}?page={page}"

    # ---------- trang danh sach ----------
    def parse_list_page(self, html: str) -> list[RawJob]:
        soup = soup_of(html)

        cards = soup.select(".job-item")
        if not cards:
            # Duong lui neu doi ten class: lay the cha cua link tin
            self.log.warning("Khong thay .job-item, dung co che du phong")
            cards = [a.parent for a in soup.select("a.job-link") if a.parent is not None]

        jobs: dict[str, RawJob] = {}
        skipped = 0
        for card in cards:
            job, reason = self._parse_card(card)
            if job is None:
                skipped += 1 if reason == "not_it" else 0
                continue
            jobs.setdefault(job.source_job_id, job)

        if skipped:
            self.log.info("  (bo qua %d tin ngoai nganh IT)", skipped)
        return list(jobs.values())

    def _parse_card(self, card) -> tuple[RawJob | None, str]:
        title_a = card.select_one("a.job-link") or card.select_one('a[href*="/tim-viec-lam/"]')
        if title_a is None:
            return None, "no_link"

        href = title_a.get("href", "")
        job_id = self.job_id_from_url(href)
        if not job_id:
            return None, "no_id"

        title = text_of(title_a, sep=" ").strip()
        if not title:
            return None, "no_title"
        if self.cfg.get("it_only", True) and not _looks_like_it_job(title):
            return None, "not_it"

        company_a = card.select_one("a.job-company") or card.select_one('a[href*="/viec-lam-cua/"]')
        company = text_of(company_a, sep=" ").strip() or None

        salary_node = card.select_one(".job-salary") or card.select_one('[class*="salary"]')
        salary = text_of(salary_node, sep=" ").strip() or None

        # Mot tin co the tuyen o nhieu tinh -> gop lai, tang clean se tach ra
        locations = [
            text_of(a, sep=" ").strip()
            for a in card.select('a[href*="/tim-viec-lam-tai/"]')
        ]
        location = " - ".join(x for x in locations if x) or None

        level_a = card.select_one("a.job-position") or card.select_one('a[href*="career_levels"]')
        career_level = text_of(level_a, sep=" ").strip() or None

        # Thoi diem cap nhat: HTML tho chi co timestamp Unix trong data-datetime,
        # phan chu ("2 gio truoc") do JavaScript dien nen requests khong thay.
        posted = None
        dt_node = card.select_one("span.cl-datetime[data-datetime]")
        if dt_node is not None:
            try:
                ts = int(dt_node["data-datetime"])
                posted = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
            except (ValueError, KeyError):
                posted = None
        if posted is None:
            for line in clean_lines(text_of(card)):
                m = POSTED_RE.match(line)
                if m:
                    posted = m.group(2).strip()
                    break

        return RawJob(
            source=self.name,
            source_job_id=job_id,
            url=urljoin(self.base_url + "/", href).split("?")[0],
            title=title,
            company=company,
            location_raw=location,
            salary_raw=salary,
            posted_raw=posted,
            skills_raw=[],                       # CareerLink khong gan tag ky nang
            extra={"career_level": career_level} if career_level else {},
        ), "ok"

    # ---------- trang chi tiet ----------
    def parse_detail_page(self, html: str, job: RawJob) -> RawJob:
        """Trang danh sach da du thong tin nen mac dinh KHONG vao chi tiet
        (fetch_detail: false) - tiet kiem 50 request moi trang. Ham nay chi
        dung khi ban bat fetch_detail de lay them mo ta."""
        soup = soup_of(html)
        main = soup.select_one("main") or soup.body or soup
        desc = text_of(main)
        if desc:
            job.description_raw = desc[:20000]
        return job
