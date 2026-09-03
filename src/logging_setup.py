"""Cau hinh logging dung chung: ghi ra console + file theo ngay."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

_FMT = "%(asctime)s | %(levelname)-7s | %(name)-22s | %(message)s"


def setup_logging(log_dir: str | Path = "logs", level: int = logging.INFO) -> logging.Logger:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = log_dir / f"pipeline_{datetime.now():%Y%m%d}.log"

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(logging.Formatter(_FMT))
    root.addHandler(stream)

    fileh = logging.FileHandler(logfile, encoding="utf-8")
    fileh.setFormatter(logging.Formatter(_FMT))
    root.addHandler(fileh)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    return root
