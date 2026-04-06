"""
Conference Scraper — Phase 2.3 Step 3
======================================

Scrapes publicly accessible conference programme pages to extract
speaker names, affiliations, and presentation titles.

Target conferences (all free, no auth required):
  - SOT  (Society of Toxicology) — March annual meeting
  - AACR (American Association for Cancer Research) — April annual meeting
  - ASHP (American Society of Health-System Pharmacists) — December midyear

Free tools used:
  - requests        — sync HTTP (run in thread pool via ConferenceService)
  - BeautifulSoup4  — HTML parser (already in requirements.txt)
  - Python re       — regex extraction
  - Python stdlib   — datetime, logging

Design principles:
  - Multi-selector fallback: if primary CSS selector returns nothing,
    try secondary selectors automatically (resilient to annual redesigns)
  - Conservative scraping: single HTTP request per page, no crawling
  - Graceful degradation: partial results > empty results > exception
  - No JavaScript execution needed: all target pages serve full HTML
"""

from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# ── HTTP settings ─────────────────────────────────────────────────────────────
_HTTP_TIMEOUT   = 15          # seconds — conference pages can be slow
_RETRY_ATTEMPTS = 2
_RETRY_DELAY    = 3.0         # seconds between retries

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Role/title keywords that signal a high-value lead ─────────────────────────
_SENIOR_ROLE_KEYWORDS = [
    "director", "head of", "vp ", "vice president", "principal",
    "senior scientist", "chief", "fellow", "professor", "pi ",
    "principal investigator", "group leader", "section chief",
]

# ── Affiliation type classifier keywords ──────────────────────────────────────
_PHARMA_KW   = ["pharma", "therapeutics", "biotech", "biosciences", "inc.", "llc", "corp"]
_ACADEMIC_KW = ["university", "institute", "college", "school of", "laboratory"]
_HOSPITAL_KW = ["hospital", "medical center", "clinic", "health system"]


# =============================================================================
# Base class
# =============================================================================

class BaseConferenceScraper(ABC):
    """
    Abstract base class for all conference scrapers.

    Subclasses must implement:
      - conference_name (property)       — short key, e.g. "sot"
      - conference_full_name (property)  — human-readable name
      - programme_urls(year)             — list of URLs to fetch
      - parse_speakers(html, url)        — extract speaker dicts from HTML
    """

    @property
    @abstractmethod
    def conference_name(self) -> str:
        """Short identifier, e.g. 'sot', 'aacr', 'ashp'"""

    @property
    @abstractmethod
    def conference_full_name(self) -> str:
        """Human-readable full name"""

    @abstractmethod
    def programme_urls(self, year: int) -> List[str]:
        """Return the list of pages to scrape for a given year."""

    @abstractmethod
    def parse_speakers(self, html: str, source_url: str) -> List[Dict[str, Any]]:
        """
        Parse HTML from a programme page and return a list of speaker dicts.

        Each dict should contain as many of these as extractable:
          name               str  (required)
          title              str
          company            str  (affiliation)
          location           str
          presentation_title str
          presentation_type  str  ("Platform Talk", "Poster", "Workshop", etc.)
          session_name       str
          email              str  (rarely available on public pages)
        """

    def scrape_speakers(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Main entry point: fetch all programme pages and extract speakers.
        Returns deduplicated list of speaker dicts.
        """
        year = year or datetime.now().year
        urls = self.programme_urls(year)

        if not urls:
            logger.warning("%s: no URLs defined for year %d", self.conference_name, year)
            return []

        all_speakers: List[Dict] = []
        seen_names: set = set()

        for url in urls:
            html = self._fetch_page(url)
            if not html:
                logger.warning("%s: failed to fetch %s", self.conference_name, url)
                continue

            speakers = self.parse_speakers(html, url)
            logger.info(
                "%s: extracted %d speakers from %s",
                self.conference_name, len(speakers), url,
            )

            for speaker in speakers:
                name = (speaker.get("name") or "").strip()
                if not name or name.lower() in seen_names:
                    continue
                speaker["conference_name"]  = self.conference_full_name
                speaker["conference_key"]   = self.conference_name
                speaker["conference_year"]  = year
                speaker["institution_type"] = _classify_institution(
                    speaker.get("company", "")
                )
                speaker["is_senior_role"]   = _is_senior_role(
                    speaker.get("title", "")
                )
                speaker["source"] = "conference"
                all_speakers.append(speaker)
                seen_names.add(name.lower())

        logger.info(
            "%s %d: total %d unique speakers",
            self.conference_name, year, len(all_speakers),
        )
        return all_speakers

    # ── Protected HTTP helper ─────────────────────────────────────────────────

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with retry logic. Returns HTML string or None."""
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                resp = requests.get(
                    url,
                    headers=_HEADERS,
                    timeout=_HTTP_TIMEOUT,
                    allow_redirects=True,
                )
                resp.raise_for_status()
                return resp.text
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    logger.info(
                        "%s: 404 for %s — URL may not exist yet",
                        self.conference_name, url,
                    )
                    return None
                logger.warning(
                    "%s: HTTP error attempt %d/%d for %s: %s",
                    self.conference_name, attempt + 1, _RETRY_ATTEMPTS, url, e,
                )
            except requests.exceptions.RequestException as e:
                logger.warning(
                    "%s: request error attempt %d/%d for %s: %s",
                    self.conference_name, attempt + 1, _RETRY_ATTEMPTS, url, e,
                )

            if attempt < _RETRY_ATTEMPTS - 1:
                time.sleep(_RETRY_DELAY)

        return None

    # ── Protected BS4 helpers ────────────────────────────────────────────────

    @staticmethod
    def _soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def _safe_get(
        tag: Optional[Tag],
        *selectors: str,
        attr: Optional[str] = None,
    ) -> str:
        """
        Try multiple CSS selectors in order; return first non-empty result.
        If attr is set, returns tag.get(attr) instead of text content.
        """
        if not tag:
            return ""
        for sel in selectors:
            found = tag.select_one(sel)
            if found:
                if attr:
                    return (found.get(attr) or "").strip()
                return found.get_text(separator=" ", strip=True)
        return ""

    @staticmethod
    def _clean_name(raw: str) -> str:
        """
        Normalise a person name extracted from HTML.
        Strips HTML entities, collapses whitespace, removes trailing
        degree suffixes (PhD, MD, DrPH, DVM, PharmD, etc.).
        """
        if not raw:
            return ""
        cleaned = re.sub(r"&[a-z]+;", " ", raw)
        cleaned = " ".join(cleaned.split())
        cleaned = re.sub(
            r",?\s*(PhD|MD|DrPH|DVM|PharmD|MPH|ScD|DSc|DDS|DMD|JD|MBA)\.?$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip(" ,")
        return cleaned

    @staticmethod
    def _clean_affiliation(raw: str) -> str:
        """Normalise an affiliation/institution string."""
        if not raw:
            return ""
        cleaned = " ".join(raw.split())
        cleaned = re.sub(r"\([A-Z]{2,3}\)$", "", cleaned).strip(" ,;")
        return cleaned


# =============================================================================
# SOT — Society of Toxicology
# =============================================================================

class SOTScraper(BaseConferenceScraper):
    """
    Scraper for the SOT Annual Meeting programme.
    URL pattern: https://www.toxicology.org/events/am/AM{YEAR}/speakers.asp
    """

    @property
    def conference_name(self) -> str:
        return "sot"

    @property
    def conference_full_name(self) -> str:
        return "Society of Toxicology Annual Meeting"

    def programme_urls(self, year: int) -> List[str]:
        base = f"https://www.toxicology.org/events/am/AM{year}"
        return [
            f"{base}/speakers.asp",
            f"{base}/sessions.asp",
            f"{base}/",
        ]

    def parse_speakers(self, html: str, source_url: str) -> List[Dict[str, Any]]:
        """
        Parse SOT programme HTML using 4 CSS selector strategies in order.
        Returns on the first strategy that yields results.
        """
        soup = self._soup(html)
        speakers: List[Dict] = []

        # Strategy 1: dedicated speaker table rows
        for row in soup.select("table.speaker-table tr, table.speakers tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            name = self._clean_name(cells[0].get_text())
            if not name:
                continue
            affiliation = self._clean_affiliation(
                cells[1].get_text() if len(cells) > 1 else ""
            )
            title_cell = cells[2].get_text() if len(cells) > 2 else ""
            speakers.append({
                "name":               name,
                "company":            affiliation,
                "title":              "Speaker",
                "presentation_title": self._clean_name(title_cell),
                "presentation_type":  "Platform Talk",
            })

        if speakers:
            return speakers

        # Strategy 2: named divs / spans
        for el in soup.select(
            "div.speaker-name, span.speaker-name, "
            "div.presenter-name, span.presenter"
        ):
            name = self._clean_name(el.get_text())
            if not name:
                continue
            parent = el.parent or el
            affil_el = parent.select_one(
                ".affiliation, .institution, .organization, .speaker-affiliation"
            )
            affiliation = self._clean_affiliation(
                affil_el.get_text() if affil_el else ""
            )
            speakers.append({
                "name":    name,
                "company": affiliation,
                "title":   "Speaker",
            })

        if speakers:
            return speakers

        # Strategy 3: profile links (href="/profile/..." or "/speaker/...")
        for link in soup.select('a[href*="/profile/"], a[href*="/speaker/"]'):
            name = self._clean_name(link.get_text())
            if not name or len(name.split()) < 2:
                continue
            parent = link.parent or link
            affil_text = parent.get_text().replace(name, "").strip(" ,;|")
            affiliation = self._clean_affiliation(affil_text[:120])
            speakers.append({
                "name":    name,
                "company": affiliation,
                "title":   "Speaker",
            })

        if speakers:
            return speakers

        # Strategy 4: bold presenter names inside session sections
        for section in soup.select("div.session, section.session, div.abstract"):
            presenter_tag = section.select_one("strong, b, .presenter")
            if not presenter_tag:
                continue
            name = self._clean_name(presenter_tag.get_text())
            if not name or len(name.split()) < 2:
                continue
            affil = ""
            for sib in presenter_tag.next_siblings:
                if hasattr(sib, "get_text"):
                    text = sib.get_text().strip()
                    if text and len(text) < 150:
                        affil = self._clean_affiliation(text)
                        break
            speakers.append({
                "name":    name,
                "company": affil,
                "title":   "Presenter",
            })

        return speakers


# =============================================================================
# AACR — American Association for Cancer Research
# =============================================================================

class AACRScraper(BaseConferenceScraper):
    """
    Scraper for the AACR Annual Meeting programme.
    URL: https://www.aacr.org/meeting/aacr-annual-meeting-{year}/
    """

    @property
    def conference_name(self) -> str:
        return "aacr"

    @property
    def conference_full_name(self) -> str:
        return "AACR Annual Meeting"

    def programme_urls(self, year: int) -> List[str]:
        return [
            f"https://www.aacr.org/meeting/aacr-annual-meeting-{year}/sessions-and-events/",
            f"https://www.aacr.org/meeting/aacr-annual-meeting-{year}/invited-speakers/",
            f"https://www.aacr.org/meeting/aacr-annual-meeting-{year}/",
        ]

    def parse_speakers(self, html: str, source_url: str) -> List[Dict[str, Any]]:
        """
        Parse AACR programme HTML using 3 strategies (card components,
        generic presenter blocks, JSON-LD structured data).
        """
        soup = self._soup(html)
        speakers: List[Dict] = []

        # Strategy 1: speaker/faculty card components
        for card in soup.select(
            "div.speaker-card, div.faculty-card, "
            "div.invited-speaker, li.speaker-item"
        ):
            name = self._safe_get(
                card,
                ".speaker-name", ".faculty-name", ".name",
                "h3", "h4", "strong",
            )
            name = self._clean_name(name)
            if not name or len(name.split()) < 2:
                continue
            affiliation = self._clean_affiliation(
                self._safe_get(
                    card,
                    ".affiliation", ".institution",
                    ".speaker-affiliation", "p.affil", "p",
                )
            )
            title_text = self._safe_get(
                card, ".speaker-title", ".position", ".role", ".faculty-title"
            )
            speakers.append({
                "name":    name,
                "company": affiliation,
                "title":   title_text or "Speaker",
            })

        if speakers:
            return speakers

        # Strategy 2: generic presenter/speaker blocks
        for el in soup.select(
            "div.presenter, span.presenter, p.presenter, "
            "span.speaker, div.speaker"
        ):
            name = self._clean_name(el.get_text())
            if not name or len(name.split()) < 2:
                continue
            parent = el.parent or el
            affil_el = parent.select_one(".affiliation, .org, em, i")
            affiliation = self._clean_affiliation(
                affil_el.get_text() if affil_el else ""
            )
            speakers.append({
                "name":    name,
                "company": affiliation,
                "title":   "Speaker",
            })

        if speakers:
            return speakers

        # Strategy 3: JSON-LD structured data
        import json
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "{}")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    performers = item.get("performer", [])
                    if not isinstance(performers, list):
                        performers = [performers]
                    for perf in performers:
                        name = self._clean_name(perf.get("name", ""))
                        if name and len(name.split()) >= 2:
                            affil = perf.get("affiliation", {})
                            org_name = (
                                affil.get("name", "") if isinstance(affil, dict)
                                else str(affil)
                            )
                            speakers.append({
                                "name":    name,
                                "company": self._clean_affiliation(org_name),
                                "title":   perf.get("jobTitle", "Speaker"),
                            })
            except Exception:
                pass

        return speakers


# =============================================================================
# ASHP — American Society of Health-System Pharmacists
# =============================================================================

class ASHPScraper(BaseConferenceScraper):
    """
    Scraper for the ASHP Midyear Clinical Meeting programme.
    URL: https://www.ashp.org/pharmacy-practice/meetings-and-events/midyear
    """

    @property
    def conference_name(self) -> str:
        return "ashp"

    @property
    def conference_full_name(self) -> str:
        return "ASHP Midyear Clinical Meeting"

    def programme_urls(self, year: int) -> List[str]:
        return [
            f"https://www.ashp.org/pharmacy-practice/meetings-and-events/midyear-{year}",
            "https://www.ashp.org/pharmacy-practice/meetings-and-events/midyear",
            f"https://midyear.ashp.org/{year}/speakers",
            "https://midyear.ashp.org/speakers",
        ]

    def parse_speakers(self, html: str, source_url: str) -> List[Dict[str, Any]]:
        """Parse ASHP programme HTML using 2 strategies."""
        soup = self._soup(html)
        speakers: List[Dict] = []

        # Strategy 1: speaker listing cards
        for card in soup.select(
            "div.speaker, div.speaker-bio, div.keynote-speaker, "
            "div.featured-speaker, li.speaker"
        ):
            name = self._safe_get(
                card,
                "h2", "h3", "h4",
                ".speaker-name", ".name", "strong", "b",
            )
            name = self._clean_name(name)
            if not name or len(name.split()) < 2:
                continue
            affiliation = self._clean_affiliation(
                self._safe_get(
                    card,
                    ".affiliation", ".organization", ".institution",
                    "p.org", "span.affiliation", "p",
                )
            )
            title_text = self._safe_get(
                card, ".title", ".position", ".role", "p.title", "span.title"
            )
            pres_title = self._safe_get(
                card, ".presentation", ".session-title", ".talk-title", "h5", "h6"
            )
            speakers.append({
                "name":               name,
                "company":            affiliation,
                "title":              title_text or "Speaker",
                "presentation_title": pres_title,
                "presentation_type":  "Session",
            })

        if speakers:
            return speakers

        # Strategy 2: article/section blocks for keynote bios
        for section in soup.select(
            "article.speaker-article, section.speaker-section, "
            "div.bio, div.speaker-profile"
        ):
            heading = section.select_one("h1, h2, h3, h4")
            if not heading:
                continue
            name = self._clean_name(heading.get_text())
            if not name or len(name.split()) < 2:
                continue
            para = section.select_one("p")
            affiliation = ""
            if para:
                affiliation = self._clean_affiliation(para.get_text()[:100])
            speakers.append({
                "name":    name,
                "company": affiliation,
                "title":   "Keynote Speaker",
            })

        return speakers


# =============================================================================
# Registry & factory
# =============================================================================

#: Map of short conference key → scraper class
SCRAPERS: Dict[str, type] = {
    "sot":  SOTScraper,
    "aacr": AACRScraper,
    "ashp": ASHPScraper,
}


def get_scraper(conference_key: str) -> BaseConferenceScraper:
    """
    Get a scraper instance by conference key.

    Args:
        conference_key: One of "sot", "aacr", "ashp"

    Raises:
        ValueError: if conference_key is not recognised
    """
    cls = SCRAPERS.get(conference_key.lower())
    if not cls:
        raise ValueError(
            f"Unknown conference '{conference_key}'. "
            f"Available: {', '.join(SCRAPERS)}"
        )
    return cls()


# =============================================================================
# Module-level helpers
# =============================================================================

def _classify_institution(affiliation: str) -> str:
    """Classify affiliation string into institution category."""
    if not affiliation:
        return "unknown"
    text = affiliation.lower()
    for kw in _ACADEMIC_KW:
        if kw in text:
            return "academic"
    for kw in _HOSPITAL_KW:
        if kw in text:
            return "hospital"
    for kw in _PHARMA_KW:
        if kw in text:
            return "pharma"
    return "unknown"


def _is_senior_role(title: str) -> bool:
    """Return True if title contains a seniority keyword."""
    if not title:
        return False
    text = title.lower()
    return any(kw in text for kw in _SENIOR_ROLE_KEYWORDS)


__all__ = [
    "BaseConferenceScraper",
    "SOTScraper",
    "AACRScraper",
    "ASHPScraper",
    "SCRAPERS",
    "get_scraper",
]
