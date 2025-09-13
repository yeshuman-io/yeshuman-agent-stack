"""
API endpoints for organisations app using Django Ninja.
"""

from ninja import Router, Schema
from typing import List
from asgiref.sync import sync_to_async
from apps.organisations.models import Organisation

# Create router for organisations endpoints
organisations_router = Router()


class OrganisationSchema(Schema):
    """Schema for Organisation model."""
    id: str
    name: str


class OrganisationCreateSchema(Schema):
    """Schema for creating an Organisation."""
    name: str


@organisations_router.get("/", response=List[OrganisationSchema], tags=["Organisations"])
async def list_organisations(request):
    """List all organisations."""
    @sync_to_async
    def get_organisations_sync():
        return list(Organisation.objects.all())

    organisations = await get_organisations_sync()
    return [
        OrganisationSchema(
            id=str(org.id),
            name=org.name
        )
        for org in organisations
    ]


@organisations_router.post("/", response=OrganisationSchema, tags=["Organisations"])
async def create_organisation(request, payload: OrganisationCreateSchema):
    """Create a new organisation."""
    @sync_to_async
    def create_organisation_sync():
        return Organisation.objects.create(
            name=payload.name
        )

    organisation = await create_organisation_sync()
    return OrganisationSchema(
        id=str(organisation.id),
        name=organisation.name
    )


@organisations_router.get("/{organisation_id}", response={200: OrganisationSchema, 404: dict}, tags=["Organisations"])
async def get_organisation(request, organisation_id: str):
    """Get a specific organisation by ID."""
    @sync_to_async
    def get_organisation_sync():
        try:
            organisation = Organisation.objects.get(id=organisation_id)
            return organisation, None
        except Organisation.DoesNotExist:
            return None, "Organisation not found"

    organisation, error = await get_organisation_sync()
    if error:
        return 404, {"error": error}

    return 200, OrganisationSchema(
        id=str(organisation.id),
        name=organisation.name
    )
