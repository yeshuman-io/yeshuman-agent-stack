"""
Evaluation services for TalentCo matching algorithms.
Handles both employer->candidate and candidate->opportunity evaluations.
"""

from typing import List, Dict, Tuple
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db import transaction

from .models import EvaluationSet, Evaluation
from apps.profiles.models import Profile, ProfileSkill
from apps.opportunities.models import Opportunity, OpportunitySkill

# PostgreSQL vector similarity imports
from pgvector.django import CosineDistance
from django.db.models import Max, Case, When, F, Value, FloatField


class EvaluationService:
    """
    Service for creating and managing evaluation sets.
    Implements multi-stage pipeline: structured -> semantic -> LLM judge
    
    Pipeline:
    1. Structured matching (skills overlap, requirements)
    2. Semantic matching (PostgreSQL vector similarity) 
    3. LLM judge (only for matches above similarity threshold)
    """
    
    def __init__(self):
        pass  # Service is stateless
    
    def create_candidate_evaluation_set(
        self, 
        opportunity_id: str,
        llm_similarity_threshold: float = 0.7
    ) -> EvaluationSet:
        """
        Employer perspective: Find best candidates for an opportunity.
        
        Pipeline:
        1. Get all profiles 
        2. Structured matching (skills overlap, basic criteria)  
        3. Semantic matching (PostgreSQL vector similarity)
        4. Rank by combined score
        5. LLM judge only matches above similarity threshold
        """
        
        with transaction.atomic():
            # Get opportunity and all profiles
            opportunity = Opportunity.objects.get(id=opportunity_id)
            all_profiles = Profile.objects.all()
            
            # Create evaluation set
            eval_set = EvaluationSet.objects.create(
                evaluator_perspective='employer',
                opportunity=opportunity,
                total_evaluated=all_profiles.count(),
                llm_threshold_percent=llm_similarity_threshold  # Note: DB field name is historic, stores similarity threshold (not percentage)
            )
            
            # Run evaluation pipeline
            scored_profiles = self._evaluate_profiles_for_opportunity(
                all_profiles, opportunity
            )
            
            # Create evaluation records
            self._create_evaluation_records(
                eval_set, scored_profiles, llm_similarity_threshold, 'employer'
            )
            
            # Mark complete
            eval_set.is_complete = True
            eval_set.completed_at = timezone.now()
            eval_set.save()
            
            return eval_set
    
    def create_opportunity_evaluation_set(
        self, 
        profile_id: str,
        llm_similarity_threshold: float = 0.7
    ) -> EvaluationSet:
        """
        Candidate perspective: Find best opportunities for a profile.
        
        Pipeline:
        1. Get all opportunities
        2. Structured matching (skills overlap, basic criteria)  
        3. Semantic matching (PostgreSQL vector similarity)
        4. Rank by combined score
        5. LLM judge only matches above similarity threshold
        """
        
        with transaction.atomic():
            # Get profile and all opportunities  
            profile = Profile.objects.get(id=profile_id)
            all_opportunities = Opportunity.objects.all()
            
            # Create evaluation set
            eval_set = EvaluationSet.objects.create(
                evaluator_perspective='candidate',
                profile=profile,
                total_evaluated=all_opportunities.count(),
                llm_threshold_percent=llm_similarity_threshold  # Note: DB field name is historic, stores similarity threshold (not percentage)
            )
            
            # Run evaluation pipeline
            scored_opportunities = self._evaluate_opportunities_for_profile(
                all_opportunities, profile
            )
            
            # Create evaluation records (swap profile/opportunity order)
            self._create_evaluation_records(
                eval_set, scored_opportunities, llm_similarity_threshold, 'candidate'
            )
            
            # Mark complete
            eval_set.is_complete = True
            eval_set.completed_at = timezone.now()
            eval_set.save()
            
            return eval_set
    
    def _evaluate_profiles_for_opportunity(
        self, 
        profiles: List[Profile], 
        opportunity: Opportunity
    ) -> List[Dict]:
        """
        Run multi-stage evaluation pipeline for profiles against opportunity.
        """
        scored_profiles = []
        
        for profile in profiles:
            # Stage 1: Structured matching
            structured_score = self._calculate_structured_match(profile, opportunity)
            
            # Stage 2: Semantic matching  
            semantic_score = self._calculate_semantic_similarity(profile, opportunity)
            
            # Combined score (weighted)
            combined_score = (structured_score * 0.6) + (semantic_score * 0.4)
            
            scored_profiles.append({
                'profile': profile,
                'opportunity': opportunity,
                'structured_score': float(structured_score),  # Convert to Python float
                'semantic_score': float(semantic_score),      # Convert to Python float
                'combined_score': float(combined_score)       # Convert to Python float
            })
        
        # Sort by combined score (highest first)
        scored_profiles.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return scored_profiles
    
    def _evaluate_opportunities_for_profile(
        self, 
        opportunities: List[Opportunity], 
        profile: Profile
    ) -> List[Dict]:
        """
        Run multi-stage evaluation pipeline for opportunities against profile.
        Same logic, different perspective.
        """
        scored_opportunities = []
        
        for opportunity in opportunities:
            # Stage 1: Structured matching
            structured_score = self._calculate_structured_match(profile, opportunity)
            
            # Stage 2: Semantic matching
            semantic_score = self._calculate_semantic_similarity(profile, opportunity)
            
            # Combined score (weighted)
            combined_score = (structured_score * 0.6) + (semantic_score * 0.4)
            
            scored_opportunities.append({
                'profile': profile,
                'opportunity': opportunity,
                'structured_score': float(structured_score),  # Convert to Python float
                'semantic_score': float(semantic_score),      # Convert to Python float
                'combined_score': float(combined_score)       # Convert to Python float
            })
        
        # Sort by combined score (highest first)
        scored_opportunities.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return scored_opportunities
    
    def _create_evaluation_records(
        self,
        eval_set: EvaluationSet,
        scored_items: List[Dict],
        similarity_threshold: float,
        perspective: str
    ) -> None:
        """
        Create Evaluation records from scored results.
        Apply LLM judge only to matches above similarity threshold.
        """
        llm_judged_count = 0
        
        for rank, item in enumerate(scored_items, 1):
            # Check if combined score exceeds similarity threshold
            should_llm_judge = item['combined_score'] >= similarity_threshold
            
            # Create base evaluation
            evaluation = Evaluation.objects.create(
                evaluation_set=eval_set,
                profile=item['profile'],
                opportunity=item['opportunity'],
                final_score=item['combined_score'],
                rank_in_set=rank,
                component_scores={
                    'structured': item['structured_score'],
                    'semantic': item['semantic_score']
                },
                was_llm_judged=should_llm_judge
            )
            
            # Apply LLM judge only if similarity is high enough
            if should_llm_judge:
                llm_score, reasoning = self._llm_judge_evaluation(
                    item['profile'], item['opportunity'], perspective
                )
                
                # Update with LLM results
                evaluation.final_score = llm_score
                evaluation.llm_reasoning = reasoning
                evaluation.component_scores['llm_judge'] = llm_score
                evaluation.save()
        
                llm_judged_count += 1
        
        # Update evaluation set with actual LLM count
        eval_set.llm_judged_count = llm_judged_count
        eval_set.save()
    
    def _calculate_structured_match(self, profile: Profile, opportunity: Opportunity) -> float:
        """
        Calculate structured matching score based on skills overlap.
        Returns score between 0.0 and 1.0.
        """
        # Get profile skills (using sync ORM - this method should be called with sync_to_async)
        profile_skills = set(
            ProfileSkill.objects.filter(profile=profile)
            .values_list('skill__name', flat=True)
        )
        
        # Get opportunity required skills
        required_skills = set(
            OpportunitySkill.objects.filter(
                opportunity=opportunity,
                requirement_type='required'
            ).values_list('skill__name', flat=True)
        )
        
        # Get opportunity preferred skills
        preferred_skills = set(
            OpportunitySkill.objects.filter(
                opportunity=opportunity,
                requirement_type='preferred'
            ).values_list('skill__name', flat=True)
        )
        
        # Calculate overlap scores
        if not required_skills and not preferred_skills:
            return 0.5  # No skills specified
        
        required_overlap = len(profile_skills & required_skills)
        preferred_overlap = len(profile_skills & preferred_skills)
        
        # Weighted scoring: required skills worth more
        required_score = required_overlap / len(required_skills) if required_skills else 1.0
        preferred_score = preferred_overlap / len(preferred_skills) if preferred_skills else 1.0
        
        # Combined score (required skills weighted 80%, preferred 20%)
        if required_skills:
            return (required_score * 0.8) + (preferred_score * 0.2)
        else:
            return preferred_score
    
    def _calculate_semantic_similarity(self, profile: Profile, opportunity: Opportunity) -> float:
        """
        Calculate multi-dimensional semantic similarity using PostgreSQL vector operations.
        
        Implements sophisticated matching strategy:
        1. Skills-to-skills matching (ProfileSkill ↔ OpportunitySkill)
        2. Experience-to-experience matching (ProfileExperience ↔ OpportunityExperience)  
        3. Skills-in-context matching (ProfileExperienceSkill ↔ OpportunitySkill) with temporal weighting
        4. Weighted combination of all dimensions
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        similarity_scores = {}
        
        # 1. Skills-to-Skills Matching (40% weight)
        skills_similarity = self._calculate_skills_similarity(profile, opportunity)
        similarity_scores['skills'] = skills_similarity
        
        # 2. Experience-to-Experience Matching (30% weight)  
        experience_similarity = self._calculate_experience_similarity(profile, opportunity)
        similarity_scores['experience'] = experience_similarity
        
        # 3. Skills-in-Context Matching with Temporal Weighting (30% weight)
        contextual_similarity = self._calculate_contextual_skills_similarity(profile, opportunity)
        similarity_scores['contextual'] = contextual_similarity
        
        # Weighted combination
        final_similarity = (
            (skills_similarity * 0.4) +
            (experience_similarity * 0.3) + 
            (contextual_similarity * 0.3)
        )
        
        return min(1.0, max(0.0, final_similarity))  # Clamp to [0, 1]
    
    def _ensure_list(self, embedding) -> List[float]:
        """Convert numpy array to list for pgvector compatibility"""
        if hasattr(embedding, 'tolist'):
            return embedding.tolist()
        elif isinstance(embedding, (list, tuple)):
            return list(embedding)
        else:
            return list(embedding)
    
    def _calculate_skills_similarity(self, profile: Profile, opportunity: Opportunity) -> float:
        """
        Calculate semantic similarity between ProfileSkills and OpportunitySkills using PostgreSQL.
        
        NOTE: This is a SYNC method with Django ORM calls - use sync_to_async when calling from async context.
        """
        
        profile_skills = profile.profile_skills.exclude(embedding__isnull=True)
        opportunity_skills = opportunity.opportunity_skills.exclude(embedding__isnull=True)
        
        if not profile_skills.exists() or not opportunity_skills.exists():
            return 0.0
        
        # For each opportunity skill, find the most similar profile skill using pgvector
        similarities = []
        
        for opp_skill in opportunity_skills:
            # Convert numpy array to list for pgvector compatibility
            opp_embedding = self._ensure_list(opp_skill.embedding)
            
            # Find the most similar profile skill using Django ORM + pgvector
            best_match = profile_skills.annotate(
                similarity=1 - CosineDistance('embedding', opp_embedding)
            ).aggregate(
                max_similarity=Max('similarity')
            )['max_similarity']
            
            similarities.append(best_match or 0.0)
        
        # Return average of best matches for each opportunity skill
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _calculate_experience_similarity(self, profile: Profile, opportunity: Opportunity) -> float:
        """
        Calculate semantic similarity between ProfileExperiences and OpportunityExperiences using PostgreSQL.
        
        NOTE: This is a SYNC method with Django ORM calls - use sync_to_async when calling from async context.
        """
        
        profile_experiences = profile.profile_experiences.exclude(embedding__isnull=True)
        opportunity_experiences = opportunity.opportunity_experiences.exclude(embedding__isnull=True)
        
        if not profile_experiences.exists() or not opportunity_experiences.exists():
            return 0.0
        
        # For each opportunity experience, find the most similar profile experience using pgvector
        similarities = []
        
        for opp_exp in opportunity_experiences:
            # Convert numpy array to list for pgvector compatibility
            opp_embedding = self._ensure_list(opp_exp.embedding)
            
            # Find the most similar profile experience using Django ORM + pgvector
            best_match = profile_experiences.annotate(
                similarity=1 - CosineDistance('embedding', opp_embedding)
            ).aggregate(
                max_similarity=Max('similarity')
            )['max_similarity']
            
            similarities.append(best_match or 0.0)
        
        # Return average of best matches for each opportunity experience
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _calculate_contextual_skills_similarity(self, profile: Profile, opportunity: Opportunity) -> float:
        """
        Calculate semantic similarity between ProfileExperienceSkills and OpportunitySkills
        with temporal weighting using PostgreSQL. This is the key innovation - skills demonstrated 
        in context with recency bias.
        
        NOTE: This is a SYNC method with Django ORM calls - use sync_to_async when calling from async context.
        """
        from apps.profiles.models import ProfileExperienceSkill
        
        opportunity_skills = opportunity.opportunity_skills.exclude(embedding__isnull=True)
        
        if not opportunity_skills.exists():
            return 0.0
        
        # Get all ProfileExperienceSkills for this profile with embeddings
        profile_exp_skills = ProfileExperienceSkill.objects.filter(
            profile_experience__profile=profile,
            embedding__isnull=False
        ).select_related('profile_experience')
        
        if not profile_exp_skills.exists():
            return 0.0
        
        # For each opportunity skill, find best matching experience skill with temporal weighting
        weighted_similarities = []
        
        for opp_skill in opportunity_skills:
            # Convert numpy array to list for pgvector compatibility
            opp_embedding = self._ensure_list(opp_skill.embedding)
            
            # Annotate experience skills with similarity and temporal weight using Django ORM
            annotated_exp_skills = profile_exp_skills.annotate(
                # Calculate cosine similarity using pgvector
                base_similarity=1 - CosineDistance('embedding', opp_embedding),
                
                # Simple temporal weight: current roles get 1.0, past roles get 0.7
                # This avoids complex date arithmetic that causes ORM issues
                temporal_weight=Case(
                    When(profile_experience__end_date__isnull=True, then=Value(1.0)),  # Current role
                    default=Value(0.7),  # Past role
                    output_field=FloatField()
                ),
                
                # Final weighted similarity
                weighted_similarity=F('base_similarity') * F('temporal_weight')
            )
            
            # Get the best weighted match for this opportunity skill
            best_weighted_match = annotated_exp_skills.aggregate(
                max_weighted=Max('weighted_similarity')
            )['max_weighted']
            
            weighted_similarities.append(best_weighted_match or 0.0)
        
        # Return average weighted similarity across all opportunity skills
        return sum(weighted_similarities) / len(weighted_similarities) if weighted_similarities else 0.0
    
    def _llm_judge_evaluation(
        self, 
        profile: Profile, 
        opportunity: Opportunity, 
        perspective: str
    ) -> Tuple[float, str]:
        """
        Use LLM to evaluate profile-opportunity match with detailed reasoning.
        Returns (score, reasoning).
        
        NOTE: This is a SYNC method with Django ORM calls - use sync_to_async when calling from async context.
        """
        import openai
        from django.conf import settings
        import json
        
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Format detailed profile data (using sync ORM - this method should be called with sync_to_async)
        profile_skills = [ps.skill.name for ps in profile.profile_skills.all()]
        
        # Get detailed experience information
        experiences = []
        for exp in profile.profile_experiences.all().order_by('-end_date'):
            exp_text = f"• {exp.title} at {exp.organisation.name} ({exp.start_date.year}-{'Present' if not exp.end_date else exp.end_date.year})"
            if exp.description:
                exp_text += f": {exp.description[:200]}..."
            experiences.append(exp_text)
        
        # Format opportunity data with more detail
        required_skills = [os.skill.name for os in opportunity.opportunity_skills.filter(requirement_type='required')]
        preferred_skills = [os.skill.name for os in opportunity.opportunity_skills.filter(requirement_type='preferred')]
        
        # Get opportunity experience requirements
        opp_experiences = []
        for opp_exp in opportunity.opportunity_experiences.all():
            opp_experiences.append(f"• {opp_exp.description}")
        
        if perspective == 'employer':
            prompt = f"""You are an expert ESG talent consultant evaluating whether a candidate is a good fit for a sustainability role.

🎯 OPPORTUNITY: {opportunity.title} at {opportunity.organisation.name}
Description: {opportunity.description}

Required Skills: {', '.join(required_skills) if required_skills else 'None specified'}
Preferred Skills: {', '.join(preferred_skills) if preferred_skills else 'None specified'}

Experience Requirements:
{chr(10).join(opp_experiences) if opp_experiences else 'None specified'}

👤 CANDIDATE: {profile.first_name} {profile.last_name}
Skills Portfolio: {', '.join(profile_skills) if profile_skills else 'None listed'}

Career History:
{chr(10).join(experiences) if experiences else 'No experience listed'}

Provide a comprehensive evaluation analyzing:
1. Skills Match: How well do their skills align with requirements?
2. Experience Relevance: How relevant is their career background?
3. Growth Potential: What's their potential for this role?
4. ESG Sector Fit: How well do they fit the ESG/sustainability domain?
5. Overall Assessment: Strengths, gaps, and recommendation

Score from 0.0 to 1.0 where:
• 0.9-1.0: Exceptional match, immediate hire
• 0.7-0.9: Strong match, proceed to interview
• 0.5-0.7: Good potential, needs further evaluation
• 0.3-0.5: Some alignment, significant gaps
• 0.0-0.3: Poor match, not suitable

Respond in JSON format: {{"score": 0.85, "reasoning": "detailed analysis here"}}"""
        else:
            prompt = f"""You are an expert career consultant evaluating whether a sustainability role is a good fit for a candidate.

👤 CANDIDATE: {profile.first_name} {profile.last_name}
Skills Portfolio: {', '.join(profile_skills) if profile_skills else 'None listed'}

Career History:
{chr(10).join(experiences) if experiences else 'No experience listed'}

🎯 OPPORTUNITY: {opportunity.title} at {opportunity.organisation.name}
Description: {opportunity.description}

Required Skills: {', '.join(required_skills) if required_skills else 'None specified'}
Preferred Skills: {', '.join(preferred_skills) if preferred_skills else 'None specified'}

Experience Requirements:
{chr(10).join(opp_experiences) if opp_experiences else 'None specified'}

Provide a comprehensive career fit analysis covering:
1. Skill Development: How does this role advance their skills?
2. Career Progression: Is this a logical next step?
3. Learning Opportunities: What new capabilities will they gain?
4. Industry Alignment: How well does this fit their ESG interests?
5. Overall Recommendation: Why this is/isn't a good move

Score from 0.0 to 1.0 where:
• 0.9-1.0: Perfect career move, highly recommended
• 0.7-0.9: Excellent opportunity, should pursue
• 0.5-0.7: Good fit, worth considering
• 0.3-0.5: Mixed fit, some benefits but gaps
• 0.0-0.3: Poor fit, not recommended

Respond in JSON format: {{"score": 0.85, "reasoning": "detailed analysis here"}}"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert ESG talent consultant with deep knowledge of sustainability careers, environmental frameworks (TCFD, GRI, SASB), and ESG investment strategies. Provide detailed, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)
            
            score = float(result.get('score', 0.0))
            reasoning = result.get('reasoning', 'LLM evaluation completed')
            
            # Clamp score to valid range
            score = max(0.0, min(1.0, score))
        
            return score, reasoning
            
        except Exception as e:
            # Fallback on API failure - return conservative score
            fallback_score = 0.7
            fallback_reasoning = f"LLM evaluation failed ({str(e)}), using conservative score"
            return fallback_score, fallback_reasoning
    
    # ================================================================
    # ASYNC AGENT METHODS - For LangGraph agent tools
    # ================================================================
    
    async def find_candidates_for_opportunity_async(
        self, 
        opportunity_id: str,
        llm_similarity_threshold: float = 0.7,
        limit: int = None
    ) -> Dict:
        """
        Async version for employer agent tools.
        Returns structured data optimized for agent consumption.
        """
        # Use sync_to_async to wrap the sync method
        sync_create = sync_to_async(self.create_candidate_evaluation_set)
        eval_set = await sync_create(opportunity_id, llm_similarity_threshold)
        
        # Get top matches 
        sync_get_evaluations = sync_to_async(
            lambda: list(eval_set.evaluations.select_related(
                'profile'
            ).order_by('rank_in_set')[:limit] if limit else eval_set.evaluations.all())
        )
        evaluations = await sync_get_evaluations()
        
        return {
            'evaluation_set_id': str(eval_set.id),
            'opportunity_id': opportunity_id,
            'total_candidates_evaluated': eval_set.total_evaluated,
            'llm_judged_count': len([e for e in evaluations if e.was_llm_judged]),
            'top_matches': [
                {
                    'rank': e.rank_in_set,
                    'profile_id': str(e.profile.id),
                    'candidate_name': f"{e.profile.first_name} {e.profile.last_name}",
                    'final_score': float(e.final_score),
                    'structured_score': float(e.component_scores.get('structured', 0)),
                    'semantic_score': float(e.component_scores.get('semantic', 0)),
                    'llm_score': float(e.component_scores.get('llm_judge')) if e.was_llm_judged else None,
                    'llm_reasoning': e.llm_reasoning if e.was_llm_judged else None,
                    'was_llm_judged': e.was_llm_judged
                } for e in evaluations
            ]
        }
    
    async def evaluate_single_candidate_async(
        self, 
        profile_id: str, 
        opportunity_id: str
    ) -> Dict:
        """
        Detailed analysis of one candidate for an opportunity.
        Used by employer agent for deep candidate evaluation.
        """
        # Get models using sync_to_async
        get_profile = sync_to_async(Profile.objects.get)
        get_opportunity = sync_to_async(Opportunity.objects.get)
        
        profile = await get_profile(id=profile_id)
        opportunity = await get_opportunity(id=opportunity_id)
        
        # Calculate all matching components (wrap sync methods with sync_to_async)
        calc_structured = sync_to_async(self._calculate_structured_match)
        calc_semantic = sync_to_async(self._calculate_semantic_similarity)
        calc_llm_judge = sync_to_async(self._llm_judge_evaluation)
        
        structured_score = await calc_structured(profile, opportunity)
        semantic_score = await calc_semantic(profile, opportunity)
        
        # Get LLM judge evaluation
        llm_score, llm_reasoning = await calc_llm_judge(profile, opportunity, 'employer')
        
        # Calculate combined score (60% structured, 40% semantic)
        combined_score = (structured_score * 0.6) + (semantic_score * 0.4)
        
        return {
            'profile_id': str(profile.id),
            'opportunity_id': str(opportunity.id),
            'candidate_name': f"{profile.first_name} {profile.last_name}",
            'detailed_scores': {
                'structured_match': float(structured_score),
                'semantic_similarity': float(semantic_score), 
                'combined_score': float(combined_score),
                'llm_judge_score': float(llm_score),
                'llm_reasoning': llm_reasoning
            },
            'skill_analysis': await self._analyze_skill_fit_async(profile, opportunity),
            'experience_analysis': await self._analyze_experience_fit_async(profile, opportunity)
        }
    
    async def find_opportunities_for_profile_async(
        self,
        profile_id: str,
        llm_similarity_threshold: float = 0.7,
        limit: int = None
    ) -> Dict:
        """
        Async version for candidate agent tools.
        Returns structured data optimized for agent consumption.
        """
        # Use sync_to_async to wrap the sync method
        sync_create = sync_to_async(self.create_opportunity_evaluation_set)
        eval_set = await sync_create(profile_id, llm_similarity_threshold)
        
        # Get top matches
        sync_get_evaluations = sync_to_async(
            lambda: list(eval_set.evaluations.select_related(
                'opportunity', 'opportunity__organisation'
            ).order_by('rank_in_set')[:limit] if limit else eval_set.evaluations.all())
        )
        evaluations = await sync_get_evaluations()
        
        return {
            'evaluation_set_id': str(eval_set.id),
            'profile_id': profile_id,
            'total_opportunities_evaluated': eval_set.total_evaluated,
            'llm_judged_count': len([e for e in evaluations if e.was_llm_judged]),
            'top_matches': [
                {
                    'rank': e.rank_in_set,
                    'opportunity_id': str(e.opportunity.id),
                    'role_title': e.opportunity.title,
                    'company_name': e.opportunity.organisation.name,
                    'final_score': float(e.final_score),
                    'structured_score': float(e.component_scores.get('structured', 0)),
                    'semantic_score': float(e.component_scores.get('semantic', 0)),
                    'llm_score': float(e.component_scores.get('llm_judge')) if e.was_llm_judged else None,
                    'llm_reasoning': e.llm_reasoning if e.was_llm_judged else None,
                    'was_llm_judged': e.was_llm_judged
                } for e in evaluations
            ]
        }
    
    async def analyze_opportunity_fit_async(
        self,
        profile_id: str,
        opportunity_id: str
    ) -> Dict:
        """
        Detailed analysis of opportunity fit for a candidate.
        Used by candidate agent for opportunity evaluation.
        """
        # Get models using sync_to_async
        get_profile = sync_to_async(Profile.objects.get)
        get_opportunity = sync_to_async(Opportunity.objects.get)
        
        profile = await get_profile(id=profile_id)
        opportunity = await get_opportunity(id=opportunity_id)
        
        # Calculate all matching components (wrap sync methods with sync_to_async)
        calc_structured = sync_to_async(self._calculate_structured_match)
        calc_semantic = sync_to_async(self._calculate_semantic_similarity)
        calc_llm_judge = sync_to_async(self._llm_judge_evaluation)
        
        structured_score = await calc_structured(profile, opportunity)
        semantic_score = await calc_semantic(profile, opportunity)
        
        # Get LLM judge evaluation from candidate perspective
        llm_score, llm_reasoning = await calc_llm_judge(profile, opportunity, 'candidate')
        
        # Calculate combined score
        combined_score = (structured_score * 0.6) + (semantic_score * 0.4)
        
        return {
            'profile_id': str(profile.id),
            'opportunity_id': str(opportunity.id),
            'role_title': opportunity.title,
            'company_name': opportunity.organisation.name,
            'fit_analysis': {
                'structured_match': float(structured_score),
                'semantic_similarity': float(semantic_score),
                'combined_score': float(combined_score),
                'llm_assessment_score': float(llm_score),
                'llm_reasoning': llm_reasoning
            },
            'skill_gap_analysis': await self._analyze_skill_gaps_async(profile, opportunity),
            'experience_relevance': await self._analyze_experience_relevance_async(profile, opportunity)
        }
    
    async def analyze_talent_pool_async(self, skill_names: List[str] = None) -> Dict:
        """
        Market insights for employer agents.
        Analyze available talent pool and skill availability.
        """
        # Get all profiles with experience data
        get_profiles = sync_to_async(
            lambda: list(Profile.objects.prefetch_related(
                'profile_skills__skill', 'profile_experiences'
            ).all())
        )
        profiles = await get_profiles()
        
        # Analyze skill distribution
        skill_analysis = {}
        experience_levels = {'junior': 0, 'mid': 0, 'senior': 0, 'executive': 0}
        
        for profile in profiles:
            # Count experience level based on total years
            # Use sync_to_async to safely access profile_experiences relationship
            def get_profile_exps_func(p):
                return list(p.profile_experiences.all())
            
            get_profile_exps = sync_to_async(get_profile_exps_func)
            profile_exps = await get_profile_exps(profile)
            
            total_experience = sum([
                ((exp.end_date or timezone.now().date()) - exp.start_date).days / 365.25
                for exp in profile_exps
            ])
            
            if total_experience < 3:
                experience_levels['junior'] += 1
            elif total_experience < 7:
                experience_levels['mid'] += 1
            elif total_experience < 15:
                experience_levels['senior'] += 1
            else:
                experience_levels['executive'] += 1
            
            # Count skills using sync_to_async
            def get_profile_skills_func(p):
                return list(p.profile_skills.select_related('skill').all())
            
            get_profile_skills = sync_to_async(get_profile_skills_func)
            profile_skill_list = await get_profile_skills(profile)
            
            for profile_skill in profile_skill_list:
                skill_name = profile_skill.skill.name
                if skill_names is None or skill_name in skill_names:
                    if skill_name not in skill_analysis:
                        skill_analysis[skill_name] = {'count': 0, 'evidence_levels': {}}
                    skill_analysis[skill_name]['count'] += 1
                    evidence = profile_skill.evidence_level
                    skill_analysis[skill_name]['evidence_levels'][evidence] = \
                        skill_analysis[skill_name]['evidence_levels'].get(evidence, 0) + 1
        
        return {
            'total_candidates': len(profiles),
            'experience_distribution': experience_levels,
            'skill_availability': skill_analysis,
            'market_insights': {
                'most_common_skills': sorted(
                    skill_analysis.items(), 
                    key=lambda x: x[1]['count'], 
                    reverse=True
                )[:10],
                'skill_scarcity': [
                    skill for skill, data in skill_analysis.items() 
                    if data['count'] < len(profiles) * 0.1  # Less than 10% have this skill
                ]
            }
        }
    
    async def get_learning_recommendations_async(
        self, 
        profile_id: str, 
        target_opportunities: List[str] = None
    ) -> Dict:
        """
        Learning and skill development recommendations for candidates.
        Analyzes skill gaps against target opportunities or market trends.
        """
        get_profile = sync_to_async(Profile.objects.get)
        profile = await get_profile(id=profile_id)
        
        # Get current skills
        current_skills = set()
        def get_profile_skills_func(p):
            return list(p.profile_skills.select_related('skill').all())
        
        get_profile_skills = sync_to_async(get_profile_skills_func)
        profile_skills = await get_profile_skills(profile)
        
        for ps in profile_skills:
            current_skills.add(ps.skill.name)
        
        # Analyze opportunities to find skill gaps
        if target_opportunities:
            def get_target_opps_func(target_ids):
                return list(Opportunity.objects.filter(
                    id__in=target_ids
                ).select_related('organisation').prefetch_related('opportunity_skills__skill'))
            
            get_target_opps = sync_to_async(get_target_opps_func)
            opportunities = await get_target_opps(target_opportunities)
        else:
            # Get all opportunities for general market analysis
            def get_all_opps_func():
                return list(Opportunity.objects.select_related('organisation').prefetch_related('opportunity_skills__skill').all())
            
            get_all_opps = sync_to_async(get_all_opps_func)
            opportunities = await get_all_opps()
        
        # Find missing skills across target opportunities
        missing_skills = {}
        recommended_skills = set()
        
        for opp in opportunities:
            opp_skills = set()
            # Use sync_to_async to safely access opportunity_skills relationship
            # Avoid lambda closure issues by creating a separate function
            def get_opp_skills_func(opportunity):
                return list(opportunity.opportunity_skills.select_related('skill').all())
            
            get_opp_skills = sync_to_async(get_opp_skills_func)
            opp_skill_list = await get_opp_skills(opp)
            
            for opp_skill in opp_skill_list:
                skill_name = opp_skill.skill.name
                opp_skills.add(skill_name)
                
                if skill_name not in current_skills:
                    if skill_name not in missing_skills:
                        missing_skills[skill_name] = {'opportunity_count': 0, 'opportunities': []}
                    missing_skills[skill_name]['opportunity_count'] += 1
                    missing_skills[skill_name]['opportunities'].append({
                        'id': str(opp.id),
                        'title': opp.title,
                        'company': opp.organisation.name
                    })
            
            # Find skills that would improve match
            skill_overlap = len(current_skills.intersection(opp_skills))
            if skill_overlap > 0:  # Only recommend for relevant opportunities
                recommended_skills.update(opp_skills - current_skills)
        
        # Prioritize recommendations
        priority_skills = sorted(
            missing_skills.items(),
            key=lambda x: x[1]['opportunity_count'],
            reverse=True
        )[:10]
        
        return {
            'profile_id': str(profile.id),
            'current_skills_count': len(current_skills),
            'skill_gap_analysis': {
                'missing_skills_count': len(missing_skills),
                'priority_recommendations': [
                    {
                        'skill_name': skill,
                        'opportunity_count': data['opportunity_count'],
                        'impact': 'high' if data['opportunity_count'] > len(opportunities) * 0.3 else 'medium',
                        'example_opportunities': data['opportunities'][:3]
                    } for skill, data in priority_skills
                ]
            },
            'learning_path': {
                'immediate_focus': [item[0] for item in priority_skills[:3]],
                'medium_term': [item[0] for item in priority_skills[3:7]],
                'advanced': [item[0] for item in priority_skills[7:]]
            }
        }
    
    # Helper methods for detailed analysis
    async def _analyze_skill_fit_async(self, profile: Profile, opportunity: Opportunity) -> Dict:
        """Analyze skill fit between profile and opportunity."""
        # Use structured matching for skill overlap (more reliable than semantic when embeddings missing)
        calc_structured_match = sync_to_async(self._calculate_structured_match)
        structured_score = await calc_structured_match(profile, opportunity)
        
        return {
            'skill_overlap_percentage': structured_score * 100,
            'matching_skills': [],  # Would be populated with actual matching skills
            'missing_skills': []    # Would be populated with required but missing skills
        }
    
    async def _analyze_experience_fit_async(self, profile: Profile, opportunity: Opportunity) -> Dict:
        """Analyze experience fit between profile and opportunity."""
        # For now, use a simple calculation based on whether profile has experiences
        # This could be enhanced with more sophisticated experience matching logic
        from asgiref.sync import sync_to_async
        
        get_profile_exp_count = sync_to_async(
            lambda: profile.profile_experiences.count()
        )
        get_opportunity_exp_count = sync_to_async(
            lambda: opportunity.opportunity_experiences.count()
        )
        
        profile_exp_count = await get_profile_exp_count()
        opp_exp_count = await get_opportunity_exp_count()
        
        # Simple heuristic: if profile has experiences and opportunity needs them, give some score
        if profile_exp_count > 0 and opp_exp_count > 0:
            experience_relevance = 0.8  # 80% as a reasonable baseline
        elif profile_exp_count > 0:
            experience_relevance = 0.6  # 60% if profile has experience but no specific requirements
        else:
            experience_relevance = 0.3  # 30% base score
        
        return {
            'experience_relevance': experience_relevance * 100,
            'relevant_experiences': [],  # Would be populated with matching experiences
            'experience_gaps': []        # Would be populated with missing experience types
        }
    
    async def _analyze_skill_gaps_async(self, profile: Profile, opportunity: Opportunity) -> Dict:
        """Analyze skill gaps for candidate perspective."""
        return await self._analyze_skill_fit_async(profile, opportunity)
    
    async def _analyze_experience_relevance_async(self, profile: Profile, opportunity: Opportunity) -> Dict:
        """Analyze experience relevance for candidate perspective."""
        return await self._analyze_experience_fit_async(profile, opportunity)


# Convenience functions for common use cases
def find_candidates_for_opportunity(opportunity_id: str, llm_similarity_threshold: float = 0.7) -> EvaluationSet:
    """Employer: Find best candidates for a job opportunity."""
    service = EvaluationService()
    return service.create_candidate_evaluation_set(opportunity_id, llm_similarity_threshold)


def find_opportunities_for_candidate(profile_id: str, llm_similarity_threshold: float = 0.7) -> EvaluationSet:
    """Candidate: Find best job opportunities for a profile."""
    service = EvaluationService()
    return service.create_opportunity_evaluation_set(profile_id, llm_similarity_threshold)


def get_top_matches(evaluation_set: EvaluationSet, limit: int = 10) -> List[Evaluation]:
    """Get top N matches from an evaluation set."""
    return evaluation_set.evaluations.order_by('rank_in_set')[:limit]


def get_llm_judged_matches(evaluation_set: EvaluationSet) -> List[Evaluation]:
    """Get only the matches that were evaluated by LLM."""
    return evaluation_set.evaluations.filter(was_llm_judged=True).order_by('rank_in_set')