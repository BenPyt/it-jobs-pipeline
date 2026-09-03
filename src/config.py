"""Doc file config.yaml va cho phep truy cap kieu cfg.crawl.http.timeout."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Cfg(dict):
    """Dict cho phep truy cap bang dau cham, de doc code hon cfg['a']['b']."""

    def __getattr__(self, item: str) -> Any:
        try:
            value = self[item]
        except KeyError as exc:  # pragma: no cover - loi cau hinh
            raise AttributeError(f"Khong co khoa cau hinh '{item}'") from exc
        return Cfg(value) if isinstance(value, dict) else value


def load_config(path: str | Path | None = None) -> Cfg:
    path = Path(path) if path else PROJECT_ROOT / "config.yaml"
    with open(path, "r", encoding="utf-8") as fh:
        return Cfg(yaml.safe_load(fh))


def resolve(rel_path: str) -> Path:
    """Doi duong dan tuong doi trong config thanh duong dan tuyet doi."""
    p = Path(rel_path)
    return p if p.is_absolute() else PROJECT_ROOT / p
