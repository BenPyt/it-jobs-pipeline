"""HTTP client dung chung cho cac scraper.

Muc tieu:
- Retry co backoff khi loi mang / 5xx / 429 (dung tenacity).
- Rate limit: nghi giua cac request + jitter, tranh dap server va tranh bi chan.
- Luu snapshot HTML thô de sau nay parse lai ma khong can crawl lai.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger(__name__)


class FetchError(RuntimeError):
    """Loi khi tai mot URL sau khi da retry het luot."""


class HttpClient:
    def __init__(
        self,
        user_agent: str,
        timeout: int = 20,
        max_retries: int = 4,
        backoff_factor: float = 1.5,
        delay_seconds: float = 1.5,
        jitter: float = 0.5,
        snapshot_dir: Path | None = None,
    ) -> None:
        self.timeout = timeout
        self.delay_seconds = delay_seconds
        self.jitter = jitter
        self.snapshot_dir = Path(snapshot_dir) if snapshot_dir else None
        if self.snapshot_dir:
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "vi,en-US;q=0.8,en;q=0.6",
                "Connection": "keep-alive",
            }
        )
        self._last_request_at = 0.0
        self._get = retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=backoff_factor, min=1, max=30),
            retry=retry_if_exception_type((requests.RequestException, FetchError)),
            reraise=True,
        )(self._get_once)

    # ---- noi bo ----
    def _respect_rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_at
        wait = self.delay_seconds - elapsed
        wait += random.uniform(0, self.jitter)
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.time()

    def _get_once(self, url: str, params: dict | None = None) -> requests.Response:
        self._respect_rate_limit()
        log.debug("GET %s params=%s", url, params)
        resp = self.session.get(url, params=params, timeout=self.timeout)
        if resp.status_code == 429 or resp.status_code >= 500:
            raise FetchError(f"HTTP {resp.status_code} tai {url}")
        resp.raise_for_status()
        return resp

    def _save_snapshot(self, url: str, html: str) -> None:
        """Luu HTML nguyen ban + ghi so muc (URL nao ung voi file nao).

        Ten file la bam SHA-1 cua URL vi URL chua '/', '?' va co the dai qua
        gioi han cua Windows. Nhung bam la mot chieu -> phai co so muc
        _index.jsonl, neu khong ta co dong HTML ma khong biet trang nao la
        trang danh sach, trang nao la trang chi tiet, thuoc nguon nao.
        """
        if not self.snapshot_dir:
            return
        key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        (self.snapshot_dir / f"{key}.html").write_text(html, encoding="utf-8")
        with open(self.snapshot_dir / "_index.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(
                {"url": url, "file": f"{key}.html",
                 "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                ensure_ascii=False) + "\n")

    # ---- API cong khai ----
    def get_html(self, url: str, params: dict | None = None) -> str:
        try:
            resp = self._get(url, params=params)
        except Exception as exc:  # noqa: BLE001 - gom moi loi mang thanh 1 kieu
            raise FetchError(f"Khong tai duoc {url}: {exc}") from exc
        html = resp.text
        self._save_snapshot(resp.url, html)
        return html
