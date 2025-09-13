"""
ESG-specific data definitions for realistic synthetic data generation.
"""

from typing import List

# ESG Skill Taxonomy
ESG_SKILLS = {
    # ESG Frameworks & Standards
    'frameworks': [
        'TCFD Framework', 'GRI Standards', 'SASB Standards', 'EU Taxonomy',
        'UN SDGs', 'ISSB Standards', 'CDP Reporting', 'CDSB Framework',
        'IIRC Integrated Reporting', 'Science Based Targets (SBTi)'
    ],
    
    # Climate & Environmental
    'climate_environmental': [
        'Carbon Accounting', 'Scope 1-3 Emissions', 'Life Cycle Assessment (LCA)',
        'Climate Scenario Analysis', 'Physical Risk Assessment', 'Transition Risk Analysis',
        'Renewable Energy', 'Water Management', 'Biodiversity Assessment',
        'Circular Economy', 'Waste Management'
    ],
    
    # Social & Governance
    'social_governance': [
        'Diversity Equity Inclusion (DEI)', 'Supply Chain Ethics', 'Human Rights Due Diligence',
        'Stakeholder Engagement', 'Board Governance', 'Executive Compensation',
        'Data Privacy', 'Cybersecurity', 'Community Investment', 'Labor Relations'
    ],
    
    # ESG Investment & Finance
    'esg_finance': [
        'ESG Integration', 'Sustainable Finance', 'Green Bonds', 'Impact Investing',
        'ESG Risk Assessment', 'Stewardship', 'Proxy Voting', 'Engagement',
        'ESG Data Analysis', 'Performance Attribution'
    ],
    
    # Technology & Analytics
    'esg_technology': [
        'ESG Data Management', 'Sustainability Reporting Software', 'Carbon Management Systems',
        'ESG Analytics', 'Python for ESG', 'R for Sustainability', 'Tableau/PowerBI',
        'SQL for ESG Data', 'API Integration', 'Data Visualization'
    ],
    
    # Regulatory & Compliance
    'regulatory': [
        'SEC Climate Disclosure', 'EU SFDR', 'EU CSRD', 'UK TCFD Compliance',
        'NFRD Implementation', 'SOX Compliance', 'Dodd-Frank', 'MiFID II ESG',
        'PRI Reporting', 'Regulatory Mapping'
    ]
}

# ESG Industries & Company Types
ESG_INDUSTRIES = {
    'asset_management': {
        'companies': ['BlackRock', 'Vanguard', 'State Street', 'Fidelity', 'T. Rowe Price', 'Wellington Management'],
        'focus_areas': ['ESG Integration', 'Stewardship', 'Climate Risk', 'Impact Investing'],
        'typical_roles': ['ESG Analyst', 'Sustainable Investment Analyst', 'Stewardship Manager', 'Climate Risk Analyst']
    },
    'banking': {
        'companies': ['JPMorgan Chase', 'Bank of America', 'Wells Fargo', 'Goldman Sachs', 'Morgan Stanley', 'Citigroup'],
        'focus_areas': ['Climate Risk', 'Sustainable Finance', 'Green Bonds', 'ESG Lending'],
        'typical_roles': ['Climate Risk Analyst', 'Sustainable Finance Manager', 'ESG Risk Manager', 'Green Bond Analyst']
    },
    'consulting': {
        'companies': ['McKinsey Sustainability', 'Deloitte ESG', 'PwC Sustainability', 'EY Climate Change', 'BCG Green'],
        'focus_areas': ['ESG Strategy', 'Net Zero Transition', 'Sustainability Transformation', 'ESG Due Diligence'],
        'typical_roles': ['ESG Consultant', 'Sustainability Manager', 'Climate Strategy Consultant', 'ESG Associate']
    },
    'corporate': {
        'companies': ['Microsoft', 'Unilever', 'Nestle', 'Apple', 'Google', 'Johnson & Johnson', 'Procter & Gamble'],
        'focus_areas': ['Corporate Sustainability', 'Supply Chain Sustainability', 'Net Zero Strategy', 'ESG Reporting'],
        'typical_roles': ['Sustainability Manager', 'ESG Director', 'Chief Sustainability Officer', 'ESG Analyst']
    },
    'esg_technology': {
        'companies': ['Sustainalytics', 'MSCI ESG', 'Refinitiv ESG', 'RepRisk', 'Carbon Trust', 'Persefoni'],
        'focus_areas': ['ESG Data', 'Carbon Management', 'ESG Analytics', 'Sustainability Software'],
        'typical_roles': ['ESG Data Analyst', 'Carbon Analyst', 'ESG Product Manager', 'Sustainability Software Engineer']
    },
    'renewable_energy': {
        'companies': ['Tesla', 'Vestas', 'Orsted', 'NextEra Energy', 'Enel Green Power', 'First Solar'],
        'focus_areas': ['Renewable Development', 'Energy Transition', 'Grid Integration', 'Clean Technology'],
        'typical_roles': ['Renewable Energy Analyst', 'Climate Project Manager', 'Energy Transition Consultant', 'Clean Tech Engineer']
    }
}

# ESG Career Personas
ESG_PERSONAS = {
    'esg_analyst': {
        'experience_range': (1, 4),
        'core_skills': ['ESG Data Analysis', 'GRI Standards', 'SASB Standards', 'ESG Research'],
        'progression_skills': ['TCFD Framework', 'Climate Scenario Analysis', 'Stakeholder Engagement'],
        'advanced_skills': ['ESG Integration', 'Impact Measurement', 'Regulatory Compliance'],
        'industries': ['asset_management', 'banking', 'consulting'],
        'title_progression': ['ESG Analyst', 'Senior ESG Analyst', 'ESG Research Manager'],
        'evidence_weights': {'evidenced': 0.5, 'experienced': 0.4, 'stated': 0.1}
    },
    
    'sustainability_consultant': {
        'experience_range': (2, 8),
        'core_skills': ['Sustainability Strategy', 'Stakeholder Engagement', 'ESG Reporting', 'Project Management'],
        'progression_skills': ['Net Zero Strategy', 'Supply Chain Sustainability', 'ESG Due Diligence'],
        'advanced_skills': ['C-Suite Advisory', 'Sustainability Transformation', 'Board Governance'],
        'industries': ['consulting', 'corporate'],
        'title_progression': ['Sustainability Consultant', 'Senior Consultant', 'Sustainability Manager', 'Director'],
        'evidence_weights': {'evidenced': 0.6, 'experienced': 0.3, 'stated': 0.1}
    },
    
    'climate_risk_specialist': {
        'experience_range': (3, 7),
        'core_skills': ['TCFD Framework', 'Climate Scenario Analysis', 'Physical Risk Assessment', 'Transition Risk Analysis'],
        'progression_skills': ['Financial Modeling', 'Stress Testing', 'Regulatory Compliance'],
        'advanced_skills': ['Climate Strategy', 'Risk Management', 'NGFS Scenarios'],
        'industries': ['banking', 'asset_management'],
        'title_progression': ['Climate Risk Analyst', 'Senior Climate Risk Analyst', 'Climate Risk Manager'],
        'evidence_weights': {'evidenced': 0.7, 'experienced': 0.2, 'stated': 0.1}
    },
    
    'impact_investment_professional': {
        'experience_range': (2, 6),
        'core_skills': ['Impact Investing', 'ESG Integration', 'Financial Analysis', 'Due Diligence'],
        'progression_skills': ['Impact Measurement', 'Sustainable Finance', 'Portfolio Management'],
        'advanced_skills': ['Fund Management', 'Impact Strategy', 'Investor Relations'],
        'industries': ['asset_management', 'consulting'],
        'title_progression': ['Impact Investment Analyst', 'Senior Analyst', 'Investment Manager'],
        'evidence_weights': {'evidenced': 0.6, 'experienced': 0.3, 'stated': 0.1}
    },
    
    'corporate_sustainability_director': {
        'experience_range': (5, 12),
        'core_skills': ['Corporate Sustainability', 'ESG Strategy', 'Stakeholder Engagement', 'Sustainability Reporting'],
        'progression_skills': ['Supply Chain Sustainability', 'Net Zero Strategy', 'Board Reporting'],
        'advanced_skills': ['C-Suite Leadership', 'Sustainability Transformation', 'Global Operations'],
        'industries': ['corporate'],
        'title_progression': ['Sustainability Manager', 'Senior Manager', 'Sustainability Director', 'Chief Sustainability Officer'],
        'evidence_weights': {'evidenced': 0.8, 'experienced': 0.2, 'stated': 0.0}
    }
}

# Career Progression Rules
CAREER_PROGRESSION = {
    'entry': {'years': (0, 2), 'titles': ['Analyst', 'Associate', 'Junior']},
    'mid': {'years': (2, 5), 'titles': ['Senior Analyst', 'Manager', 'Senior Associate']},
    'senior': {'years': (5, 8), 'titles': ['Senior Manager', 'Director', 'Principal']},
    'executive': {'years': (8, 15), 'titles': ['Senior Director', 'VP', 'Chief']}
}

# ESG Technology Timeline (for temporal authenticity)
ESG_TECHNOLOGY_TIMELINE = {
    2015: ['UN SDGs adopted', 'Paris Agreement'],
    2017: ['TCFD recommendations', 'EU Action Plan on Sustainable Finance'],
    2018: ['IPCC 1.5°C report', 'EU Taxonomy development'],
    2019: ['EU Green Deal announced', 'SASB standards finalized'],
    2020: ['EU Taxonomy Regulation', 'TCFD widespread adoption'],
    2021: ['ISSB formation', 'SEC climate risk guidance'],
    2022: ['EU SFDR implementation', 'IRA passage'],
    2023: ['EU CSRD implementation', 'ISSB standards finalized'],
    2024: ['SEC climate disclosure rules', 'EU Due Diligence Directive']
}

def get_skills_for_year(year: int) -> List[str]:
    """Return skills that would be relevant for a given year based on ESG evolution"""
    relevant_skills = []
    
    # Add foundational skills always available
    relevant_skills.extend(['ESG Research', 'Sustainability Reporting', 'Stakeholder Engagement'])
    
    # Add skills based on timeline
    if year >= 2017:
        relevant_skills.extend(['TCFD Framework', 'Climate Risk Assessment'])
    if year >= 2018:
        relevant_skills.extend(['EU Taxonomy', 'Transition Risk Analysis'])
    if year >= 2020:
        relevant_skills.extend(['SFDR Compliance', 'Climate Scenario Analysis'])
    if year >= 2022:
        relevant_skills.extend(['ISSB Standards', 'SEC Climate Disclosure'])
    if year >= 2024:
        relevant_skills.extend(['CSRD Implementation', 'EU Due Diligence'])
    
    return relevant_skills