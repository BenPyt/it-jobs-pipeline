"""Doc/ghi tang du lieu tho (raw).

Dinh dang: JSONL - moi DONG la mot object JSON doc lap.

Vi sao khong dung JSON thuong: file JSON chi hop le khi ket thuc bang ']'.
Neu crawler chet giua chung (mat mang, Ctrl+C, het pin) thi file cut = file
hong, mat sach cong crawl. Voi JSONL, moi dong tu no da hop le: cut dong cuoi
chi mat dung tin do. Nho vay ta ghi duoc TUNG TIN ngay khi lay duoc, thay vi
gom het trong RAM roi ghi mot lan o cuoi.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterator

log = logging.getLogger(__name__)


class RawWriter:
    """Ghi tung tin xuong dia ngay lap tuc (append-only).

    Dung nhu context manager:
        with RawWriter(path) as writer:
            for job in scraper.scrape():
                writer.write(job.to_dict())
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = None
        self.count = 0

    def __enter__(self) -> "RawWriter":
        # "a" = append: khong ghi de noi dung cu, va file duoc tao neu chua co
        self._fh = open(self.path, "a", encoding="utf-8")
        return self

    def write(self, record: dict[str, Any]) -> None:
        assert self._fh is not None, "RawWriter phai dung trong khoi 'with'"
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        # flush() day du lieu ra khoi bo dem cua Python ngay -> crash van con du lieu.
        # Doi lai: cham hon mot chut. Voi crawler (nghi 1.5s giua cac request)
        # thi chi phi nay khong dang ke.
        self._fh.flush()
        self.count += 1

    def __exit__(self, *exc_info) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None


def read_raw(path: str | Path) -> list[dict[str, Any]]:
    """Doc file raw. Ho tro ca .jsonl (moi dong 1 tin) lan .json (mot mang) cu.

    Dong hong (vd dong cuoi bi cut vi crash) duoc bo qua kem canh bao,
    thay vi lam sap toan bo lan chay.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    if path.suffix == ".json":
        return json.loads(text)

    records: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            log.warning("Bo qua dong hong %s:%d (co the do lan crawl truoc bi ngat)",
                        path.name, lineno)
    return records


def iter_raw(path: str | Path) -> Iterator[dict[str, Any]]:
    """Doc lan luot tung dong - dung khi file raw lon hon RAM."""
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
