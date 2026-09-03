"""Cac scraper theo nguon. Them nguon moi = them 1 file + dang ky o SCRAPERS."""
from .base import BaseScraper, RawJob
from .itviec import ITviecScraper
from .topcv import TopCVScraper

SCRAPERS = {
    ITviecScraper.name: ITviecScraper,
    TopCVScraper.name: TopCVScraper,
}

__all__ = ["BaseScraper", "RawJob", "SCRAPERS", "ITviecScraper", "TopCVScraper"]
