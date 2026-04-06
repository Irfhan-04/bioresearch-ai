"""
PubMed API Integration for Lead Discovery
Finds researchers who publish on relevant topics
"""

from typing import List, Dict, Optional
from Bio import Entrez
from datetime import datetime, timedelta
import time
import re


class PubMedScraper:
    """
    Scrapes PubMed for authors of relevant publications
    Uses official NCBI Entrez API (legal and free)
    """
    
    # Relevant search terms for 3D in-vitro models
    RELEVANT_TERMS = [
        "drug-induced liver injury",
        "DILI",
        "hepatotoxicity",
        "3D cell culture",
        "organoid",
        "spheroid",
        "organ-on-chip",
        "microphysiological systems",
        "in vitro toxicity",
        "liver models",
        "hepatocyte culture",
        "NAM",
        "new approach methodologies"
    ]
    
    def __init__(self, email: str = "user@example.com", api_key: Optional[str] = None):
        """
        Initialize PubMed scraper
        
        Args:
            email: Email for Entrez API (required by NCBI)
            api_key: Optional API key for higher rate limits
        """
        Entrez.email = email
        if api_key:
            Entrez.api_key = api_key
        
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def search_pubmed(
        self,
        query: str,
        max_results: int = 100,
        years_back: int = 3,
        retmode: str = "xml"
    ) -> List[str]:
        """
        Search PubMed for article IDs
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            years_back: Only include papers from last N years
            
        Returns:
            List of PubMed IDs
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years_back * 365)
        
        # Format dates for PubMed
        date_range = f"{start_date.year}/{start_date.month:02d}/{start_date.day:02d}:{end_date.year}/{end_date.month:02d}/{end_date.day:02d}"
        
        try:
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                datetype="pdat",
                mindate=f"{start_date.year}",
                maxdate=f"{end_date.year}",
                sort="relevance"
            )
            
            record = Entrez.read(handle)
            handle.close()
            
            return record.get("IdList", [])
        
        except Exception as e:
            print(f"Error searching PubMed: {e}")
            return []
    
    def fetch_article_details(self, pmid_list: List[str]) -> List[Dict]:
        """
        Fetch detailed article information
        
        Args:
            pmid_list: List of PubMed IDs
            
        Returns:
            List of article details
        """
        if not pmid_list:
            return []
        
        articles = []
        
        try:
            # Fetch in batches of 50
            batch_size = 50
            for i in range(0, len(pmid_list), batch_size):
                batch = pmid_list[i:i + batch_size]
                
                handle = Entrez.efetch(
                    db="pubmed",
                    id=",".join(batch),
                    retmode="xml"
                )
                
                records = Entrez.read(handle)
                handle.close()
                
                for record in records.get("PubmedArticle", []):
                    try:
                        article = self._parse_article(record)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        print(f"Error parsing article: {e}")
                        continue
                
                # Rate limiting
                time.sleep(0.34)  # NCBI recommends max 3 requests/second
        
        except Exception as e:
            print(f"Error fetching articles: {e}")
        
        return articles
    
    def _parse_article(self, record: Dict) -> Optional[Dict]:
        """
        Parse article record into structured data
        
        Args:
            record: PubMed article record
            
        Returns:
            Parsed article data
        """
        try:
            medline = record.get("MedlineCitation", {})
            article = medline.get("Article", {})
            
            # Extract title
            title = article.get("ArticleTitle", "")
            
            # Extract abstract
            abstract = ""
            if "Abstract" in article and "AbstractText" in article["Abstract"]:
                abstract_parts = article["Abstract"]["AbstractText"]
                if isinstance(abstract_parts, list):
                    abstract = " ".join([str(part) for part in abstract_parts])
                else:
                    abstract = str(abstract_parts)
            
            # Extract publication date
            pub_date = article.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
            year = pub_date.get("Year", "")
            
            # Extract authors
            authors = []
            author_list = article.get("AuthorList", [])
            for author in author_list:
                last_name = author.get("LastName", "")
                fore_name = author.get("ForeName", "")
                affiliation = ""
                
                if "AffiliationInfo" in author and author["AffiliationInfo"]:
                    affiliation = author["AffiliationInfo"][0].get("Affiliation", "")
                
                if last_name:
                    authors.append({
                        "last_name": last_name,
                        "first_name": fore_name,
                        "full_name": f"{fore_name} {last_name}".strip(),
                        "affiliation": affiliation
                    })
            
            # Extract PMID
            pmid = medline.get("PMID", "")
            
            return {
                "pmid": str(pmid),
                "title": title,
                "abstract": abstract,
                "year": year,
                "authors": authors,
                "journal": article.get("Journal", {}).get("Title", "")
            }
        
        except Exception as e:
            print(f"Error parsing article: {e}")
            return None
    
    def extract_corresponding_author(self, article: Dict) -> Optional[Dict]:
        """
        Extract the corresponding author (usually PI with budget)
        
        Args:
            article: Parsed article data
            
        Returns:
            Corresponding author information
        """
        authors = article.get("authors", [])
        
        if not authors:
            return None
        
        # Strategy: Last author is usually the corresponding author / PI
        # In biomedical research, the last author is typically the senior researcher
        corresponding = authors[-1] if authors else None
        
        if corresponding:
            # Extract company/institution from affiliation
            affiliation = corresponding.get("affiliation", "")
            company = self._extract_company(affiliation)
            location = self._extract_location(affiliation)
            
            return {
                "name": corresponding["full_name"],
                "affiliation": affiliation,
                "company": company,
                "location": location,
                "role": "Corresponding Author"
            }
        
        return None
    
    def _extract_company(self, affiliation: str) -> str:
        """
        Extract company/institution name from affiliation string
        
        Args:
            affiliation: Affiliation text
            
        Returns:
            Company name
        """
        if not affiliation:
            return "Unknown"
        
        # Common patterns
        # "Department of X, Company Name, Location"
        # "Company Name, Department of X, Location"
        
        # Split by comma and take likely candidates
        parts = [p.strip() for p in affiliation.split(",")]
        
        if len(parts) >= 2:
            # Usually company is first or second part
            for part in parts[:2]:
                # Skip department names
                if not any(kw in part.lower() for kw in ["department", "division", "center", "institute"]):
                    return part
            
            # Fallback to first part
            return parts[0]
        
        return affiliation[:100] if affiliation else "Unknown"
    
    def _extract_location(self, affiliation: str) -> str:
        """
        Extract location from affiliation string
        
        Args:
            affiliation: Affiliation text
            
        Returns:
            Location string
        """
        if not affiliation:
            return "Unknown"
        
        # Look for common location patterns
        # Usually last part after comma
        parts = [p.strip() for p in affiliation.split(",")]
        
        if len(parts) >= 2:
            # Check last few parts for location indicators
            for part in reversed(parts[-2:]):
                # Look for city/state/country patterns
                if any(indicator in part.lower() for indicator in ["usa", "uk", "ma", "ca", "ny"]):
                    return part
            
            # Fallback to last part
            return parts[-1]
        
        return "Unknown"
    
    def search_authors(
        self,
        query: str,
        max_results: int = 50,
        years_back: int = 3
    ) -> List[Dict]:
        """
        Search for authors publishing on a topic
        
        Args:
            query: Search query
            max_results: Max number of articles to process
            years_back: Only include recent papers
            
        Returns:
            List of potential leads with publication data
        """
        print(f"Searching PubMed for: {query}")
        
        # Search PubMed
        pmid_list = self.search_pubmed(query, max_results, years_back)
        
        if not pmid_list:
            print("No articles found")
            return []
        
        print(f"Found {len(pmid_list)} articles, fetching details...")
        
        # Fetch article details
        articles = self.fetch_article_details(pmid_list)
        
        print(f"Processed {len(articles)} articles, extracting leads...")
        
        # Extract unique corresponding authors
        leads = []
        seen_names = set()
        
        for article in articles:
            author = self.extract_corresponding_author(article)
            
            if author and author["name"] not in seen_names:
                lead = {
                    "name": author["name"],
                    "title": "Principal Investigator",  # Assumption based on corresponding author
                    "company": author["company"],
                    "location": author["location"],
                    "company_hq": author["location"],
                    "email": "N/A",  # Would need email enrichment
                    "linkedin": "N/A",
                    "recent_publication": True,
                    "publication_year": int(article.get("year", datetime.now().year)),
                    "publication_title": article.get("title", ""),
                    "company_funding": "Unknown",
                    "uses_3d_models": True,  # Assumption based on search
                    "tenure_months": 24,
                    "pubmed_id": article.get("pmid", ""),
                    "journal": article.get("journal", "")
                }
                
                leads.append(lead)
                seen_names.add(author["name"])
        
        print(f"Extracted {len(leads)} unique leads")
        
        return leads
    
    def search_multiple_terms(
        self,
        terms: Optional[List[str]] = None,
        max_results_per_term: int = 20
    ) -> List[Dict]:
        """
        Search multiple relevant terms and combine results
        
        Args:
            terms: List of search terms (uses defaults if None)
            max_results_per_term: Max results per term
            
        Returns:
            Combined list of leads
        """
        terms = terms or self.RELEVANT_TERMS[:3]  # Use top 3 terms by default
        
        all_leads = []
        seen_names = set()
        
        for term in terms:
            print(f"\n--- Searching: {term} ---")
            leads = self.search_authors(term, max_results_per_term, years_back=2)
            
            # Deduplicate
            for lead in leads:
                if lead["name"] not in seen_names:
                    all_leads.append(lead)
                    seen_names.add(lead["name"])
        
        return all_leads


# Example usage
if __name__ == "__main__":
    # Initialize scraper
    scraper = PubMedScraper(email="test@example.com")
    
    # Test single search
    leads = scraper.search_authors(
        query="drug-induced liver injury 3D models",
        max_results=10
    )
    
    print(f"\nFound {len(leads)} leads:")
    for lead in leads[:3]:
        print(f"\n- {lead['name']}")
        print(f"  Company: {lead['company']}")
        print(f"  Publication: {lead['publication_title'][:80]}...")