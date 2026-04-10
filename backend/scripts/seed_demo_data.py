"""Populate BioResearch AI with demo researchers from PubMed."""

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.core.database import AsyncSessionLocal
from app.models.researcher import Researcher
from app.services.enrichment_service import EnrichmentService
from app.services.pubmed_service import PubMedService

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
log = logging.getLogger(__name__)

DEMO_QUERIES = [
    ('drug induced liver injury hepatotoxicity organoids', 6),
    ('hepatic spheroid 3D model DILI', 4),
    ('preclinical drug safety assessment toxicology ADME', 6),
    ('safety pharmacology hERG cardiotoxicity', 4),
    ('organ on chip microphysiological system', 6),
    ('microfluidics tissue engineering in vitro model', 4),
    ('drug discovery target validation phenotypic screening', 6),
    ('preclinical ADME pharmacokinetics drug candidate', 4),
    ('hepatotoxicity biomarker clinical translation', 6),
    ('DILI biomarker panel translational safety', 4),
]


async def seed():
    pubmed = PubMedService()
    enrichment = EnrichmentService()
    seeded = 0

    async with AsyncSessionLocal() as db:
        for query, max_results in DEMO_QUERIES:
            log.info("Fetching PubMed results for: '%s'", query)
            try:
                raw_profiles = await pubmed.search_researchers(query=query, max_results=max_results)
            except Exception as exc:
                log.error("PubMed fetch failed for '%s': %s", query, exc)
                continue

            for profile in raw_profiles:
                existing = await db.scalar(select(Researcher).where(Researcher.full_name == profile.get('full_name')))
                if existing:
                    continue

                try:
                    researcher = await enrichment.enrich_and_save(db=db, raw_profile=profile)
                    await db.commit()
                    log.info("Seeded: %s | area=%s | score=%s | tier=%s", researcher.full_name, researcher.research_area, researcher.relevance_score, researcher.relevance_tier)
                    seeded += 1
                except Exception as exc:
                    await db.rollback()
                    log.error("Failed to enrich %s: %s", profile.get('full_name', 'unknown'), exc)

    log.info('Seed complete — %s researchers added to DB and ChromaDB index.', seeded)
    if seeded < 20:
        log.warning('WARNING: fewer than 20 researchers seeded. Flexibility Test may fail.')


if __name__ == '__main__':
    asyncio.run(seed())
