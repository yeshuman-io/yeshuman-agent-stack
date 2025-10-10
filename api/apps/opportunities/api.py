"""
API endpoints for opportunities app using Django Ninja.
"""

from ninja import Router, Schema
from typing import List, Optional
from django.db.models import Q, F, Value
from apps.opportunities.models import Opportunity, OpportunitySkill, OpportunityExperience

# Create router for opportunities endpoints
opportunities_router = Router()


class OpportunitySkillSchema(Schema):
    """Schema for OpportunitySkill model."""
    id: str
    skill_name: str
    requirement_type: str


class OpportunityExperienceSchema(Schema):
    """Schema for OpportunityExperience model."""
    id: str
    description: str


class OpportunitySchema(Schema):
    """Schema for Opportunity model."""
    id: str
    title: str
    description: str
    location: str
    organisation_name: str
    skills: List[OpportunitySkillSchema]
    experiences: List[OpportunityExperienceSchema]


class OpportunityCreateSchema(Schema):
    """Schema for creating an Opportunity."""
    title: str
    description: str
    organisation_id: str


class PaginatedOpportunitiesResponse(Schema):
    """Paginated response for opportunities list."""
    results: List[OpportunitySchema]
    page: int
    page_size: int
    total: int
    has_next: bool


@opportunities_router.get("/", response=PaginatedOpportunitiesResponse, tags=["Opportunities"])
def list_opportunities(
    request,
    q: Optional[str] = None,
    organisation: Optional[str] = None,
    location: Optional[str] = None,
    mode: str = "hybrid",
    page: int = 1,
    page_size: int = 20
):
    """List opportunities with search, filters, and pagination."""
    from apps.embeddings.services import EmbeddingService

    def build_queryset():
        queryset = Opportunity.objects.prefetch_related(
            'organisation', 'opportunity_skills__skill', 'opportunity_experiences'
        )

        # Apply filters
        if organisation:
            queryset = queryset.filter(organisation__name__icontains=organisation)
        if location:
            queryset = queryset.filter(location__icontains=location)

        # Apply search based on mode
        if q:
            if mode == "keyword":
                # Keyword search using ILIKE
                queryset = queryset.filter(
                    Q(title__icontains=q) | Q(description__icontains=q)
                )
            elif mode == "semantic" and hasattr(Opportunity, 'embedding'):
                # Semantic search using embeddings
                from pgvector.django import CosineDistance

                service = EmbeddingService()
                query_embedding = service.generate_embedding(q)

                queryset = queryset.annotate(
                    similarity=1 - CosineDistance('embedding', query_embedding)
                ).filter(similarity__gt=0.1).order_by('-similarity')
            elif mode == "hybrid" and hasattr(Opportunity, 'embedding'):
                # Hybrid search: try semantic first, fallback to keyword
                from pgvector.django import CosineDistance

                service = EmbeddingService()
                query_embedding = service.generate_embedding(q)

                # First try semantic search
                semantic_results = queryset.annotate(
                    similarity=1 - CosineDistance('embedding', query_embedding)
                ).filter(similarity__gt=0.1).order_by('-similarity')

                # If no semantic results, fallback to keyword
                if not semantic_results.exists():
                    return queryset.filter(
                        Q(title__icontains=q) | Q(description__icontains=q)
                    )
                else:
                    return semantic_results
            else:
                # Fallback to keyword if mode is invalid or embeddings missing
                queryset = queryset.filter(
                    Q(title__icontains=q) | Q(description__icontains=q)
                )

        return queryset

    def paginate_and_serialize(queryset, page, page_size):
        # Calculate pagination
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size

        opportunities = list(queryset[start:end])

        # Serialize results
        results = []
        for opp in opportunities:
            results.append(OpportunitySchema(
                id=str(opp.id),
                title=opp.title,
                description=opp.description,
                location=opp.location,
                organisation_name=opp.organisation.name,
                skills=[
                    OpportunitySkillSchema(
                        id=str(skill.id),
                        skill_name=skill.skill.name,
                        requirement_type=skill.requirement_type
                    )
                    for skill in opp.opportunity_skills.all()
                ],
                experiences=[
                    OpportunityExperienceSchema(
                        id=str(exp.id),
                        description=exp.description
                    )
                    for exp in opp.opportunity_experiences.all()
                ]
            ))

        return PaginatedOpportunitiesResponse(
            results=results,
            page=page,
            page_size=page_size,
            total=total,
            has_next=total > page * page_size
        )

    queryset = build_queryset()
    response = paginate_and_serialize(queryset, page, page_size)
    return response


@opportunities_router.post("/", response=OpportunitySchema, tags=["Opportunities"])
async def create_opportunity(request, payload: OpportunityCreateSchema):
    """Create a new opportunity."""
    from asgiref.sync import sync_to_async
    from apps.organisations.models import Organisation

    organisation = await sync_to_async(Organisation.objects.get)(id=payload.organisation_id)

    opportunity = await sync_to_async(Opportunity.objects.create)(
        title=payload.title,
        description=payload.description,
        organisation=organisation
    )
    return OpportunitySchema(
        id=str(opportunity.id),
        title=opportunity.title,
        description=opportunity.description,
        organisation_name=opportunity.organisation.name,
        skills=[],
        experiences=[]
    )


@opportunities_router.get("/{opportunity_id}/questions", response=List[dict], tags=["Opportunities"])
async def get_opportunity_questions(request, opportunity_id: str):
    """Get screening questions for an opportunity."""
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_questions_sync():
        try:
            opportunity = Opportunity.objects.get(id=opportunity_id)
            questions = opportunity.questions.all().order_by('order')
            return list(questions)
        except Opportunity.DoesNotExist:
            return None

    questions = await get_questions_sync()
    if questions is None:
        return []

    return [
        {
            'id': str(q.id),
            'question_text': q.question_text,
            'question_type': q.question_type,
            'is_required': q.is_required,
            'order': q.order,
            'config': q.config
        }
        for q in questions
    ]


@opportunities_router.get("/{opportunity_id}", response=OpportunitySchema, tags=["Opportunities"])
async def get_opportunity(request, opportunity_id: str):
    """Get a specific opportunity by ID."""
    from asgiref.sync import sync_to_async

    opportunity = await sync_to_async(Opportunity.objects.prefetch_related('organisation', 'opportunity_skills__skill', 'opportunity_experiences').get)(id=opportunity_id)
    return OpportunitySchema(
        id=str(opportunity.id),
        title=opportunity.title,
        description=opportunity.description,
        organisation_name=opportunity.organisation.name,
        skills=[
            OpportunitySkillSchema(
                id=str(skill.id),
                skill_name=skill.skill.name,
                requirement_type=skill.requirement_type
            )
            for skill in opportunity.opportunity_skills.all()
        ],
        experiences=[
            OpportunityExperienceSchema(
                id=str(exp.id),
                description=exp.description
            )
            for exp in opportunity.opportunity_experiences.all()
        ]
    )
