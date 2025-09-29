# Django App Structure Planning Document

## Current State Analysis

### Existing Django Projects
We have two Django projects in the codebase:

1. **Main API** (`/api/`): YesHuman multi-tenant platform with 4 clients
2. **TalentCo API** (`/talentco/api/`): TalentCo-specific Django project

### Current App Structure
Both projects contain identical Django apps in their `apps/` directories:

**Available Apps:**
- `applications` - Job application management
- `embeddings` - Vector embeddings for AI/ML
- `evaluations` - Performance/candidate evaluations
- `memories` - Memory management (Mem0 integration)
- `opportunities` - Job opportunity management
- `organisations` - Organization management
- `profiles` - User/candidate profiles
- `skills` - Skills taxonomy and matching
- `testing` - Testing utilities
- `api` - API layer (unclear purpose)

### Client-Specific App Requirements Analysis

Based on business domain analysis, here are the apps needed by each client:

**TalentCo (Talent/Recruitment):**
- `accounts` - User management/authentication (renamed from `auth` to follow Django best practices)
- `profiles` - User profiles (candidates, recruiters, etc.)
- `organisations` - Organization management
- `applications` - Job application management
- `opportunities` - Job opportunities (managed as "projects")
- `evaluations` - Performance/candidate evaluations
- `memories` - Memory management (Mem0 integration)
- `skills` - Skills taxonomy and matching
- `threads` - Conversation threads (may relate to opportunities/projects)
- `embeddings` - Vector embeddings for AI/ML (shared)
- `seed` - Data seeding utilities (renamed from testing)

**Lumie (Health/Wellness):**
- `accounts` - User management/authentication (renamed from `auth` to follow Django best practices)
- `profiles` - User profiles
- `threads` - Conversation threads
- `memories` - Memory management
- `records` - Health/wellness records
- `consultations` - Health consultations

**BookedAI (Travel/Booking):**
- `accounts` - User management/authentication (renamed from `auth` to follow Django best practices)
- `itineraries` - Travel itineraries (abstract | instantiated)
- `threads` - Conversation threads
- `memories` - Memory management
- `artefacts` - Points of interest, events, persons, historical references

**YesHuman (Agency Platform):**
- `accounts` - User management/authentication (renamed from `auth` to follow Django best practices)
- `clients` - Client/tenant management (core agency functionality - managing multiple client accounts)
- `organisations` - Organization management (agency and client organizations)
- `threads` - Conversation threads
- `profiles` - User profiles (agency staff and clients)
- `memories` - Memory management (conversation history across clients)
- `projects` - Project management (agency projects across different clients)
- `billing` - Billing and invoicing (agency financial management)
- Potentially other agency-specific apps as business needs evolve

### Shared vs Client-Specific Apps Analysis

**Shared Apps (appear in multiple clients):**
- `accounts` - All clients need user management (renamed from `auth` to follow Django best practices)
- `profiles` - All clients need user profiles
- `organisations` - Multiple clients need organization management
- `threads` - All clients need conversation threads
- `memories` - All clients need memory management
- `embeddings` - **CONFIRMED SHARED**: AI/ML embeddings infrastructure (OpenAI integration, pgvector setup, batch processing)

**Client-Specific Apps:**
- `applications`, `opportunities`, `evaluations`, `skills` - TalentCo specific
- `records`, `consultations` - Lumie specific
- `itineraries`, `artefacts` - BookedAI specific
- `clients`, `projects`, `billing` - YesHuman platform specific

### Standard Django App File Structure

**Based on our identified apps, each Django app should contain these core files:**

```
apps/[app_name]/
├── __init__.py                    # Package marker
├── apps.py                        # App configuration
├── api.py                         # Django Ninja API endpoints (if app has API)
├── models.py                      # Database models
├── factories.py                   # Factory Boy factories (simple, for unit testing)
├── services.py                    # Business logic services (if needed)
├── management/                    # Management commands (if needed)
│   └── commands/
│       └── [command_name].py
├── migrations/                    # Database migrations
│   └── __init__.py
└── tests/                         # Comprehensive test suite
    ├── __init__.py
    ├── conftest.py               # pytest fixtures (if needed)
    ├── test_models.py            # Model tests
    ├── test_api.py               # API endpoint tests (if app has API)
    ├── test_services.py          # Service tests
    ├── test_factories.py         # Factory tests
    └── integration/              # Integration tests for this app
        └── test_[feature].py
```

**App-Specific Variations Based on Our Apps:**

**For API-Heavy Apps** (accounts/auth, threads, etc.):
- `api.py` - Django Ninja routers and endpoints (following current pattern)
- `test_api.py` - API endpoint tests

**For Data-Processing Apps** (embeddings, data_gen):
- `services.py` - Core business logic (embeddings has this)
- `generators.py` - Content generators (data_gen has this)
- `factories.py` - Complex cross-app factories (data_gen only)
- `fixtures/` - Sample data files (data_gen has this)

**For Apps with Management Commands** (embeddings, data_gen):
- `management/commands/` - Django management commands

**Not All Apps Need All Files:**
- Apps without API endpoints won't need `api.py` or `test_api.py`
- Apps without complex business logic won't need `services.py`
- Apps without management commands won't need `management/`
- Simple model-only apps may have minimal additional files

**Key Files That All Apps Should Have:**
- `__init__.py`, `apps.py`, `models.py`, `tests/`, `factories.py`
- `migrations/` (if the app has models)
- `api.py` (if the app exposes API endpoints)

**Django Ninja API Pattern:**
Each app with API endpoints should have an `api.py` file defining a router (e.g., `accounts_router`, `threads_router`). The main `yeshuman/api.py` imports and registers these routers with `api.add_router("/app_name", app_router, tags=["App Name"])`.

### Embeddings App Analysis & Recommendation

**Current State:**
- **Generic Service**: OpenAI text-embedding-3-small integration with batch processing
- **Infrastructure**: Sets up pgvector extension (PostgreSQL vector storage)
- **Management Commands**: For generating embeddings across models
- **Currently TalentCo-focused**: But service architecture is client-agnostic

**Recommendation: KEEP AS SHARED APP**
- **Why**: All clients will need AI/embedding capabilities for semantic search, recommendations, etc.
- **Infrastructure**: pgvector setup is required for any vector operations
- **Service Quality**: Well-architected, generic API that can serve multiple clients
- **Future-Proof**: Can be extended for different embedding models/providers

**Migration Plan:**
- Keep in shared infrastructure (core or shared directory)
- Update model references to be client-agnostic
- Make embedding generation configurable per client if needed

### Current Django Settings Configuration

**Main API (`yeshuman/settings.py`):**
- Multi-tenant setup with `CLIENT_CONFIG` environment variable
- Currently only has core apps: `auth`, `threads`, `a2a`
- No talentco apps integrated yet

**TalentCo API (`talentco/settings.py`):**
- Single-tenant configuration
- Includes all the talentco apps: applications, skills, evaluations, etc.
- Uses Mem0 for memory management

## Key Questions & Decisions Needed

### 1. Client-Specific App Requirements

**Question:** Which of the existing talentco apps should be available to each client?

**Current Clients:**
- **YesHuman**: Full platform experience (general-purpose AI assistant)
- **BookedAI**: Travel/booking focused
- **TalentCo**: Talent/recruitment focused
- **Lumie**: Health/wellness focused

**Possible App Categorization:**
- **Universal Apps**: Available to all clients (e.g., profiles, organisations)
- **Client-Specific Apps**: Only relevant to certain clients
- **Optional Apps**: Can be enabled/disabled per client

### 2. App Generalization Strategy

**Question:** Which talentco apps need to be made more generic to work across different domains?

**Current TalentCo Apps Analysis:**
- `applications` - Very TalentCo-specific (job applications, hiring pipeline)
- `opportunities` - Could be generalized to "projects" or "engagements"
- `evaluations` - Could be generalized to "assessments" or "reviews"
- `profiles` - Already fairly generic
- `organisations` - Already generic
- `skills` - Could be generalized to "capabilities" or "attributes"
- `embeddings` - Already generic (AI/ML)
- `memories` - Already generic (Mem0 integration)

### 3. Proposed App Structure

**Question:** What should the final Django app structure look like?

Based on your preference for top-level organization (not by domain initially), here are two options:

**Option A: Flat Structure (Your Preference)**
```
apps/
├── accounts/               # User management (renamed from auth, follows Django best practices)
├── profiles/               # User profiles
├── organisations/          # Organization management
├── clients/                # Client/tenant management (agency core functionality)
├── threads/                # Conversation threads
├── memories/               # Memory management
├── projects/               # Comprehensive project management (YesHuman agency)
├── billing/                # Billing/invoicing (YesHuman agency)
├── applications/           # Job applications (TalentCo)
├── opportunities/          # Job opportunities (TalentCo)
├── skills/                 # Skills management (TalentCo)
├── records/                # Health records (Lumie)
├── consultations/          # Health consultations (Lumie)
├── itineraries/            # Travel itineraries (BookedAI)
├── artefacts/              # Travel artefacts (BookedAI)
├── embeddings/             # AI/ML embeddings (KEEP - shared infrastructure)
└── seed/                   # Data seeding utilities (renamed from testing)
```

**Option B: Domain-Grouped (Future Evolution)**
```
apps/
├── core/                   # Universal apps
│   ├── accounts/           # User management (renamed from auth)
│   ├── profiles/
│   ├── organisations/      # Organization management
│   ├── threads/
│   └── memories/
├── agency/                 # YesHuman agency platform
│   ├── clients/            # Client management
│   ├── projects/           # Agency project management
│   └── billing/            # Agency billing/invoicing
├── talent/                 # TalentCo domain
│   ├── applications/       # Job applications
│   ├── opportunities/      # Job opportunities
│   └── skills/
├── health/                 # Lumie domain
│   ├── records/
│   └── consultations/      # Health consultations
├── travel/                 # BookedAI domain
│   ├── itineraries/        # Travel itineraries
│   └── artefacts/          # Travel artefacts
└── shared/                 # Infrastructure
    ├── embeddings/         # AI/ML embeddings (shared infrastructure)
    └── seed/               # Data seeding utilities (renamed from testing)
```

### 4. Settings Configuration Strategy

**Question:** How should Django INSTALLED_APPS be configured for multi-tenancy?

**Options:**
1. **Static Configuration**: All apps always installed, runtime checks for client access
2. **Dynamic Configuration**: Different INSTALLED_APPS per client
3. **Feature Flags**: Apps always installed but features conditionally enabled

### 5. Migration Strategy

**Question:** How to handle existing data and migrations when restructuring?

**Current State:**
- TalentCo apps have their own migrations
- Main API has no talentco app migrations yet
- Need to consider data migration between old and new structures

## Proposed Implementation Plan

### Phase 1: Analysis & Planning
- [ ] Complete client app requirements analysis
- [ ] Identify which apps need generalization
- [ ] Design final app structure
- [ ] Plan migration strategy

### Phase 2: App Generalization
- [ ] Generalize talentco-specific apps to work across domains
- [ ] Update model field names, help text, and business logic
- [ ] Ensure backward compatibility where possible

### Phase 3: Structure Implementation (Flat Structure)
- [ ] Use flat app structure (Option A) as decided
- [ ] Leverage existing TalentCo apps as foundation
- [ ] Fix imports and ensure pgvector DB setup
- [ ] Update Django settings: install all apps, use runtime checks

### Phase 4: Shared Apps First (MVP - 1-2 apps at a time)
- [ ] Start with shared apps: accounts, profiles, organisations, threads, memories
- [ ] Establish patterns and tests for each app
- [ ] Gradually bring apps online and validate functionality
- [ ] TalentCo client configuration as priority

### Phase 5: Client-Specific Apps & Testing
- [ ] Add TalentCo-specific apps: applications, opportunities, evaluations, skills
- [ ] Implement remaining clients: Lumie, BookedAI
- [ ] Reorganize tests: move unit tests to app-level, organize integration tests
- [ ] Distribute factories: create simple app-level factories, move complex to seed
- [ ] Update pytest configuration for new test structure
- [ ] Create/refactor management commands for sample data generation

## Updated Implementation Plan

### Phase 1: App Inventory & Naming
- [ ] Confirm final app names: auth→accounts, testing→seed, add evaluations
- [ ] Plan migration: rename auth→accounts and testing→seed, update imports, settings, URLs
- [ ] Include evaluations app in TalentCo client setup

### Phase 2: Shared App Strategy
- [ ] Make shared apps (accounts, memories) general enough to serve all clients
- [ ] Implement runtime feature checks for client-specific behavior
- [ ] Use Option A: All apps always installed with runtime checks

### Phase 3: Structure Implementation
- [ ] Choose between flat (Option A) or domain-grouped (Option B) structure
- [ ] Move/refactor existing apps to new structure
- [ ] Update Django settings for multi-tenant app loading

### Phase 4: Client Integration
- [ ] Implement client-specific app enabling/disabling
- [ ] Test each client's app configuration
- [ ] Validate data models work across clients

### Test & Data Organization Strategy

**Current Test Structure:**
- Project-level `tests/` directory with integration tests
- `pytest.ini` and `conftest.py` for pytest configuration
- `apps/testing/` → rename to `apps/data_gen/` (contains factories and data generators)
- Individual test files scattered in project root

**Factory Purposes (Dual Use):**
- **Testing**: Generate realistic test data with proper relationships
- **Sample Data**: Populate interfaces with demo content (including LLM-generated data)

**Recommended Test & Data Organization:**

Each app follows the [Standard Django App File Structure](#standard-django-app-file-structure) above, with these key files for testing:

```
apps/
├── accounts/
│   ├── tests/              # Unit tests (see standard structure)
│   └── factories.py        # Factory Boy factories (testing + sample data)
├── profiles/
│   ├── tests/              # Unit tests
│   └── factories.py        # Factory Boy factories
├── organisations/
│   ├── tests/              # Unit tests
│   └── factories.py        # Factory Boy factories
├── clients/
│   ├── tests/              # Unit tests
│   └── factories.py        # Factory Boy factories
├── threads/
│   ├── tests/              # Unit tests
│   └── factories.py        # Factory Boy factories
├── memories/
│   ├── tests/              # Unit tests
│   └── factories.py        # Factory Boy factories
├── projects/
│   ├── tests/              # Unit tests
│   └── factories.py        # Factory Boy factories
├── billing/
│   ├── tests/              # Unit tests
│   └── factories.py        # Factory Boy factories
├── applications/
│   ├── tests/              # Unit tests (TalentCo)
│   └── factories.py        # Factory Boy factories
├── opportunities/
│   ├── tests/              # Unit tests (TalentCo)
│   └── factories.py        # Factory Boy factories
├── skills/
│   ├── tests/              # Unit tests (TalentCo)
│   └── factories.py        # Factory Boy factories
├── records/
│   ├── tests/              # Unit tests (Lumie)
│   └── factories.py        # Factory Boy factories
├── consultations/
│   ├── tests/              # Unit tests (Lumie)
│   └── factories.py        # Factory Boy factories
├── itineraries/
│   ├── tests/              # Unit tests (BookedAI)
│   └── factories.py        # Factory Boy factories
├── artefacts/
│   ├── tests/              # Unit tests (BookedAI)
│   └── factories.py        # Factory Boy factories
└── seed/                   # Central data generation service
    ├── factories.py        # Cross-app factories (ESG data, complex relationships)
    ├── generators.py       # LLM-generated content generators
    ├── management/commands/# Django management commands for data seeding
    ├── tests/              # Tests for data generation utilities
    └── fixtures/           # JSON fixtures for sample/demo data

# Integration & E2E Tests (project level)
tests/
├── integration/           # Multi-app integration tests
├── e2e/                  # End-to-end tests
├── client_specific/      # Client-specific integration tests
│   ├── talentco/
│   ├── lumie/
│   ├── bookedai/
│   └── yeshuman/
└── fixtures/             # Shared test fixtures (JSON, etc.)

# Pytest Configuration (project root)
pytest.ini
conftest.py
```

**Factory & Generator Relationship Resolution:**

**App-Level Factories** (`apps/[app]/factories.py`):
- **Purpose**: Simple model factories for unit testing each app in isolation
- **Scope**: Only models from that specific app
- **Content**: Basic Factory Boy factories without complex relationships
- **Usage**: Primary use is testing - create test data for app-specific tests

**Data Gen App** (`apps/data_gen/`):
- **Purpose**: Complex data generation for development, demos, and cross-app scenarios
- **Scope**: Cross-app relationships, realistic sample data, LLM generation
- **Contains**:
  - `generators.py` - LLM content generators (ESGContentGenerator)
  - `factories.py` - Complex cross-app factories with relationships
  - `fixtures/` - Sample data files
  - `management/commands/` - Data seeding commands

**Relationship & Usage Pattern:**
1. **Simple Testing**: Use app-level `factories.py` for isolated unit tests
2. **Complex Testing**: Use `data_gen` factories for integration tests with relationships
3. **Development Data**: Use `data_gen` management commands for realistic sample data
4. **Content Generation**: App factories can import generators from `data_gen` for realistic text content

**Example Usage:**
```python
# In profiles/tests/test_models.py (simple testing)
from profiles.factories import ProfileFactory

# In data_gen/factories.py (complex relationships)
from profiles.factories import ProfileFactory
from organisations.factories import OrganisationFactory
from data_gen.generators import ESGContentGenerator

# Management command uses generators for LLM content
generator = ESGContentGenerator()
description = generator.generate_experience_description(context)
```

**Test Categories:**
- **Unit Tests**: In each app's `tests/` directory (test app logic)
- **Integration Tests**: Project-level `tests/` directory (test cross-app workflows)
- **Client-Specific Tests**: Organized by client in `tests/client_specific/`
- **E2E Tests**: Full application flow tests

## Open Questions for Discussion

### 1. **App Naming & Scope Confirmation**

**Django Naming Best Practices (Based on Django 5.2 Documentation):**
Django recommends **NOT** naming custom authentication apps "auth" to avoid confusion with `django.contrib.auth`. Common alternatives:
- `accounts` - User accounts and authentication
- `users` - User management
- `authentication` - Explicit authentication functionality

Your current `auth` app contains:
- Custom User model extending AbstractUser
- JWT authentication endpoints (register/login)
- Authentication backend and middleware

**Recommendation:** Rename `auth` → `accounts` (following Django best practices to avoid confusion with `django.contrib.auth`)

**YesHuman as Agency Platform Impact:**
Since YesHuman is an agency platform serving multiple clients, it will likely need:
- More comprehensive project management (beyond just opportunities)
- Billing/invoicing capabilities
- Client relationship management
- Agency-specific workflows

**Decisions Made:**
- ✅ **Auth → Accounts**: Yes, rename `auth` app to `accounts` (follows Django best practices)
- ✅ **Evaluations**: Most definitely include (it's in current TalentCo codebase and needed)
- ✅ **Agency-specific apps**: Leave as is for now; we'll address in later iterations
- ✅ **Embeddings app**: Confirmed to keep as shared infrastructure
- ✅ **Testing app**: Renamed to `seed` for data seeding utilities

### 2. **Shared App Architecture**
**Decision: Unsure yet - discuss when closer to implementation**
- Ideally make shared apps general enough to serve all clients
- Memories and accounts will be shared in the least (most client-specific)
- Will revisit when implementing specific apps

### 3. **Multi-Tenant App Loading**
**Decision: Option A - All apps always installed**
- Install all apps in INSTALLED_APPS
- Use runtime feature checks for client-specific behavior
- Simplest approach for initial implementation

### 4. **Structure Preference**
**Decision: Option A (Flat)**
- Keep flat app structure as initially suggested
- Will organize as the number of apps grows (subdirectories if needed)
- Domain-grouped structure can be considered in future iterations

### 5. **Migration Strategy**
**Decision: Leverage existing TalentCo apps**
- The TalentCo apps are mostly everything we want
- Fix imports and ensure DB setup supports pgvector
- Refactor in-place with migration scripts where needed
- Preserve existing TalentCo data during transition

### 6. **Priority & Rollout**
**Decision: TalentCo first priority**
- **Client Priority**: TalentCo (existing codebase)
- **MVP Scope**: Start with shared apps first (1-2 apps at a time)
- **Implementation Approach**: Bring apps online gradually, establish patterns and tests, then move forward
- **Rollout**: Shared apps → Client-specific apps → Multi-tenant integration

## ✅ Specification Finalized

All key decisions have been made! The Django app structure specification is now complete and ready for implementation.

**Next Steps:**
1. Start with Phase 1: App naming (auth→accounts, testing→seed)
2. Move to Phase 4: Implement shared apps first (1-2 at a time)
3. Focus on TalentCo client as priority
4. Establish patterns and tests before expanding to other clients

The planning document now serves as the complete blueprint for the multi-tenant Django application structure.
