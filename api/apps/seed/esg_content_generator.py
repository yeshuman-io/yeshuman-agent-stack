"""
ESG-focused content generation using LLM for realistic synthetic data.
"""

import openai
import random
from typing import Dict, List, Any
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ESGContentGenerator:
    """
    Generates realistic ESG-focused content for profiles and opportunities.
    Uses GPT-4 for ultra-realistic career narratives and job descriptions.
    """
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4"  # Best quality for content generation
    
    def generate_experience_description(self, context: Dict[str, Any]) -> str:
        """
        Generate realistic ESG experience description.
        
        Args:
            context: {
                'title': 'ESG Analyst',
                'company': 'BlackRock',
                'industry': 'asset_management',
                'duration_months': 24,
                'skills': ['TCFD', 'ESG Analysis'],
                'seniority': 'mid',
                'previous_role': 'Junior ESG Associate'
            }
        """
        prompt = f"""Generate a realistic 2-3 sentence professional experience description for an ESG role:

Role: {context['title']}
Company: {context['company']} ({context['industry']})
Duration: {context['duration_months']} months
Key Skills: {', '.join(context['skills'])}
Seniority Level: {context['seniority']}
Previous Role: {context.get('previous_role', 'N/A')}

Requirements:
- Write in first person past tense
- Include specific ESG projects, frameworks, or achievements
- Mention concrete outcomes or metrics where relevant
- Reference real ESG frameworks (TCFD, GRI, SASB, EU Taxonomy, etc.)
- Keep professional tone, 2-3 sentences maximum
- Make it authentic to the ESG industry

Example: "Led ESG integration analysis for $50B equity portfolio using SASB materiality frameworks. Developed climate risk assessment methodology incorporating TCFD scenarios, resulting in 15% portfolio carbon intensity reduction. Collaborated with portfolio managers to implement ESG tilting strategies across 200+ holdings."
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.8  # Higher creativity for varied content
            )
            
            description = response.choices[0].message.content.strip()
            logger.info(f"Generated ESG experience description for {context['title']}")
            return description
            
        except Exception as e:
            logger.error(f"Failed to generate ESG experience: {e}")
            return self._fallback_experience_description(context)
    
    def generate_job_description(self, context: Dict[str, Any]) -> str:
        """
        Generate realistic ESG job posting description.
        
        Args:
            context: {
                'title': 'Senior Climate Risk Analyst',
                'company': 'JPMorgan Chase',
                'industry': 'banking',
                'required_skills': ['TCFD', 'Scenario Analysis'],
                'preferred_skills': ['Python', 'Financial Modeling'],
                'seniority': 'senior'
            }
        """
        prompt = f"""Generate a realistic ESG job posting description:

Role: {context['title']}
Company: {context['company']} ({context['industry']})
Required Skills: {', '.join(context['required_skills'])}
Preferred Skills: {', '.join(context['preferred_skills'])}
Seniority: {context['seniority']}

Requirements:
- Professional corporate tone
- Include specific ESG responsibilities and deliverables
- Reference relevant frameworks, regulations, or industry standards
- Mention stakeholder interaction (internal teams, clients, regulators)
- Include growth opportunities or strategic impact
- 3-4 sentences maximum
- Make it authentic to {context['industry']} industry ESG needs

Example: "Lead climate risk assessment for commercial lending portfolio using NGFS scenarios and TCFD framework. Develop stress testing methodologies for physical and transition risks across $100B loan book. Partner with risk management teams to integrate climate factors into credit decisioning processes. Support regulatory reporting including upcoming SEC climate disclosure requirements."
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
                temperature=0.7
            )
            
            description = response.choices[0].message.content.strip()
            logger.info(f"Generated ESG job description for {context['title']}")
            return description
            
        except Exception as e:
            logger.error(f"Failed to generate ESG job description: {e}")
            return self._fallback_job_description(context)
    
    def generate_opportunity_experience_requirement(self, context: Dict[str, Any]) -> str:
        """
        Generate specific experience requirements for ESG opportunities.
        
        Args:
            context: {
                'role_focus': 'climate_risk',
                'industry': 'banking',
                'seniority': 'senior',
                'specific_frameworks': ['TCFD', 'NGFS']
            }
        """
        prompt = f"""Generate a specific ESG experience requirement for a job posting:

Role Focus: {context['role_focus']}
Industry: {context['industry']}
Seniority: {context['seniority']}
Frameworks: {', '.join(context['specific_frameworks'])}

Create a 1-2 sentence requirement that specifies:
- Years of experience needed
- Specific ESG frameworks or methodologies required
- Industry context or sector expertise
- Type of projects or responsibilities

Example: "3+ years of experience implementing TCFD recommendations in financial services, including physical and transition risk scenario analysis. Proven track record developing climate stress testing methodologies for loan portfolios or investment strategies."
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.6
            )
            
            requirement = response.choices[0].message.content.strip()
            logger.info(f"Generated ESG experience requirement for {context['role_focus']}")
            return requirement
            
        except Exception as e:
            logger.error(f"Failed to generate ESG experience requirement: {e}")
            return self._fallback_experience_requirement(context)
    
    def _fallback_experience_description(self, context: Dict[str, Any]) -> str:
        """Fallback if LLM generation fails"""
        skills_text = ', '.join(context['skills'][:3])  # First 3 skills
        return f"Worked as {context['title']} at {context['company']} focusing on {skills_text}. Contributed to ESG initiatives and sustainability reporting. Gained expertise in ESG frameworks and stakeholder engagement."
    
    def _fallback_job_description(self, context: Dict[str, Any]) -> str:
        """Fallback if LLM generation fails"""
        required_skills = ', '.join(context['required_skills'][:3])
        return f"Seeking {context['title']} to lead ESG initiatives at {context['company']}. Responsibilities include {required_skills} and sustainability reporting. Opportunity to drive ESG strategy and stakeholder engagement."
    
    def _fallback_experience_requirement(self, context: Dict[str, Any]) -> str:
        """Fallback if LLM generation fails"""
        years = "3+" if context['seniority'] == 'senior' else "2+"
        frameworks = ', '.join(context['specific_frameworks'])
        return f"{years} years of experience with {frameworks} in {context['industry']} sector. Proven track record in ESG analysis and reporting."