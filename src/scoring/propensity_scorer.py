"""
Propensity Scoring Algorithm for Lead Prioritization
Calculates probability of engagement based on weighted criteria
"""

from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd


class PropensityScorer:
    """
    Scoring engine that calculates lead propensity scores based on:
    - Role Fit (30 points default)
    - Recent Publications (40 points default)
    - Company Funding (20 points default)
    - Strategic Location (10 points default)
    """
    
    # Target keywords for role fit
    ROLE_KEYWORDS = [
        'toxicology', 'toxicologist', 'safety', 'preclinical',
        'hepatic', 'liver', '3d', 'in vitro', 'in-vitro',
        'drug induced', 'dili', 'adme', 'safety assessment',
        'safety pharmacology', 'nonclinical', 'director',
        'head', 'vp', 'chief', 'lead', 'principal'
    ]
    
    # Strategic biotech/pharma hubs
    STRATEGIC_LOCATIONS = [
        'cambridge', 'boston', 'bay area', 'san francisco',
        'south san francisco', 'san diego', 'basel', 'oxford',
        'cambridge uk', 'london', 'seattle', 'new jersey'
    ]
    
    # High-value funding stages
    FUNDED_STAGES = ['series a', 'series b', 'series c', 'ipo', 'public']
    
    # Relevant technology keywords
    TECH_KEYWORDS = [
        '3d', 'organoid', 'spheroid', 'organ-on-chip',
        'microphysiological', 'in vitro', 'nam', 'nams',
        'new approach methodologies'
    ]
    
    def __init__(self, weights: Optional[Dict[str, int]] = None):
        """
        Initialize scorer with custom weights
        
        Args:
            weights: Dictionary with keys: role_fit, publication, funding, location
        """
        self.weights = weights or {
            'role_fit': 30,
            'publication': 40,
            'funding': 20,
            'location': 10
        }
        
        # Validate weights sum to 100
        total = sum(self.weights.values())
        if total != 100:
            raise ValueError(f"Weights must sum to 100, got {total}")
    
    def calculate_score(self, lead: pd.Series) -> int:
        """
        Calculate overall propensity score for a lead
        
        Args:
            lead: Pandas Series with lead information
            
        Returns:
            Score between 0-100
        """
        score = 0
        
        # 1. Role Fit Score
        score += self._score_role_fit(lead)
        
        # 2. Publication Score
        score += self._score_publication(lead)
        
        # 3. Funding Score
        score += self._score_funding(lead)
        
        # 4. Location Score
        score += self._score_location(lead)
        
        # Ensure score is between 0-100
        return max(0, min(100, int(score)))
    
    def _score_role_fit(self, lead: pd.Series) -> float:
        """
        Score based on job title relevance
        
        High value roles:
        - Contains toxicology/safety keywords: Full weight
        - Contains 3D/in-vitro keywords: 80% weight
        - Senior role (Director, VP, Head): +20% bonus
        """
        title = str(lead.get('title', '')).lower()
        score = 0
        max_score = self.weights['role_fit']
        
        # Check for primary keywords
        primary_match = any(kw in title for kw in ['toxicology', 'safety', 'hepatic'])
        tech_match = any(kw in title for kw in ['3d', 'in vitro', 'in-vitro'])
        
        if primary_match:
            score = max_score
        elif tech_match:
            score = max_score * 0.8
        elif any(kw in title for kw in self.ROLE_KEYWORDS):
            score = max_score * 0.6
        else:
            score = max_score * 0.2  # Everyone gets some baseline
        
        # Bonus for seniority
        seniority_keywords = ['director', 'head', 'vp', 'chief', 'lead', 'principal']
        if any(kw in title for kw in seniority_keywords):
            score *= 1.2  # 20% bonus
        
        return min(score, max_score)
    
    def _score_publication(self, lead: pd.Series) -> float:
        """
        Score based on recent relevant publications
        
        Scoring:
        - Published in last 2 years on relevant topic: Full weight
        - Published but older: 50% weight
        - No publication: 10% weight (still valuable)
        """
        max_score = self.weights['publication']
        
        has_recent_pub = lead.get('recent_publication', False)
        pub_year = lead.get('publication_year', 0)
        pub_title = str(lead.get('publication_title', '')).lower()
        
        current_year = datetime.now().year
        
        if has_recent_pub and pub_year >= current_year - 2:
            # Check if publication is highly relevant
            if any(kw in pub_title for kw in ['dili', 'liver injury', '3d', 'organoid', 'toxicity']):
                return max_score  # Perfect match
            else:
                return max_score * 0.8  # Recent but less relevant
        
        elif pub_year > 0 and pub_year >= current_year - 5:
            return max_score * 0.5  # Older publication
        
        else:
            return max_score * 0.1  # No recent publication (still has baseline value)
    
    def _score_funding(self, lead: pd.Series) -> float:
        """
        Score based on company funding status
        
        Scoring:
        - Series A/B/C: Full weight (has budget to buy)
        - Public/IPO: 80% weight (established, may have budget)
        - Seed/Early: 40% weight (limited budget)
        - Unknown: 20% weight (baseline)
        """
        max_score = self.weights['funding']
        funding = str(lead.get('company_funding', '')).lower()
        
        if any(stage in funding for stage in ['series a', 'series b', 'series c']):
            return max_score  # Prime buying stage
        
        elif any(stage in funding for stage in ['public', 'ipo']):
            return max_score * 0.8  # Established companies
        
        elif 'seed' in funding or 'early' in funding:
            return max_score * 0.4  # Limited budget
        
        else:
            return max_score * 0.2  # Unknown funding
    
    def _score_location(self, lead: pd.Series) -> float:
        """
        Score based on strategic location
        
        Scoring:
        - Major biotech hub: Full weight
        - Secondary hub: 60% weight
        - Other location: 20% weight (still valuable for remote work)
        """
        max_score = self.weights['location']
        location = str(lead.get('location', '')).lower()
        
        # Check for primary hubs
        if any(hub in location for hub in ['cambridge, ma', 'boston', 'bay area', 'basel']):
            return max_score
        
        # Check for secondary hubs
        elif any(hub in location for hub in self.STRATEGIC_LOCATIONS):
            return max_score * 0.6
        
        else:
            return max_score * 0.2  # Remote work is still valuable
    
    def get_score_breakdown(self, lead: pd.Series) -> Dict[str, float]:
        """
        Get detailed breakdown of score components
        
        Returns:
            Dictionary with individual component scores
        """
        return {
            'role_fit': self._score_role_fit(lead),
            'publication': self._score_publication(lead),
            'funding': self._score_funding(lead),
            'location': self._score_location(lead),
            'total': self.calculate_score(lead)
        }
    
    def score_batch(self, leads_df: pd.DataFrame) -> pd.DataFrame:
        """
        Score multiple leads at once
        
        Args:
            leads_df: DataFrame with lead information
            
        Returns:
            DataFrame with added 'propensity_score' and 'rank' columns
        """
        df = leads_df.copy()
        
        # Calculate scores
        df['propensity_score'] = df.apply(self.calculate_score, axis=1)
        
        # Calculate rank (1 = highest score)
        df['rank'] = df['propensity_score'].rank(ascending=False, method='min').astype(int)
        
        # Sort by rank
        df = df.sort_values('rank').reset_index(drop=True)
        
        return df
    
    def get_priority_tier(self, score: int) -> str:
        """
        Categorize lead into priority tier
        
        Args:
            score: Propensity score (0-100)
            
        Returns:
            Priority tier: 'High', 'Medium', or 'Low'
        """
        if score >= 70:
            return 'High'
        elif score >= 50:
            return 'Medium'
        else:
            return 'Low'
    
    def explain_score(self, lead: pd.Series) -> str:
        """
        Generate human-readable explanation of score
        
        Returns:
            Text explanation of scoring factors
        """
        breakdown = self.get_score_breakdown(lead)
        total = breakdown['total']
        tier = self.get_priority_tier(total)
        
        explanation = f"""
Lead Score: {total}/100 ({tier} Priority)

Score Breakdown:
• Role Fit: {breakdown['role_fit']:.1f}/{self.weights['role_fit']} points
  - Job title: {lead.get('title', 'N/A')}
  
• Publication: {breakdown['publication']:.1f}/{self.weights['publication']} points
  - Recent publication: {lead.get('recent_publication', False)}
  - Year: {lead.get('publication_year', 'N/A')}
  
• Funding: {breakdown['funding']:.1f}/{self.weights['funding']} points
  - Company stage: {lead.get('company_funding', 'Unknown')}
  
• Location: {breakdown['location']:.1f}/{self.weights['location']} points
  - Based in: {lead.get('location', 'N/A')}

Recommendation: {"HIGH priority outreach - strong fit!" if tier == 'High' 
                 else "Medium priority - good potential" if tier == 'Medium' 
                 else "Lower priority - consider for nurture campaign"}
"""
        return explanation.strip()


# Example usage and testing
if __name__ == "__main__":
    # Test with sample lead
    sample_lead = pd.Series({
        'name': 'Dr. Sarah Mitchell',
        'title': 'Director of Toxicology',
        'company': 'Moderna Therapeutics',
        'location': 'Cambridge, MA',
        'recent_publication': True,
        'publication_year': 2024,
        'publication_title': 'Novel 3D hepatic models for DILI assessment',
        'company_funding': 'Public',
        'uses_3d_models': True
    })
    
    # Initialize scorer
    scorer = PropensityScorer()
    
    # Calculate score
    score = scorer.calculate_score(sample_lead)
    print(f"Propensity Score: {score}/100")
    
    # Get breakdown
    breakdown = scorer.get_score_breakdown(sample_lead)
    print(f"\nBreakdown: {breakdown}")
    
    # Get explanation
    explanation = scorer.explain_score(sample_lead)
    print(f"\n{explanation}")