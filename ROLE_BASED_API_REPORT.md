# Focus-Based Tool & API Integration Report

## Executive Summary
Transform generic tools into focus-aware implementations that enable seamless agent-driven and UI-driven data management through unified APIs with intelligent permission filtering.

## Current State Analysis
- ✅ User Focus System: `negotiate_user_focus()` determines candidate/employer/admin roles
- ✅ Generic Tools: `list_profiles`, `find_opportunities_for_profile` work for all roles
- ✅ Agent Integration: Tools are loaded dynamically, agent can call them
- ❌ Missing: Focus-aware tool behavior, unified API endpoints, intelligent filtering

## Proposed Architecture: Focus-Specific Tool Development

### 1. Purpose-Built Tools Per Focus

#### Candidate-Focused Tools
```python
CANDIDATE_TOOLS = [
    # Profile Management (Self-Service)
    ManageMyProfileTool(),           # CRUD own profile
    BrowsePublicProfilesTool(),      # Network with other candidates

    # Job Search & Applications
    SearchOpportunitiesTool(),       # Find jobs matching profile
    ViewOpportunityDetailsTool(),    # Deep dive into job postings
    SubmitApplicationTool(),         # Apply to opportunities
    TrackApplicationStatusTool(),    # Monitor application progress

    # Career Development
    GetCareerRecommendationsTool(),  # Personalized advice
    SkillGapAnalysisTool(),          # Identify improvement areas
]
```

#### Employer-Focused Tools
```python
EMPLOYER_TOOLS = [
    # Opportunity Management (Owned Content)
    CreateJobPostingTool(),          # Post new opportunities
    ManageMyPostingsTool(),           # Edit/update owned opportunities
    ArchiveJobPostingTool(),          # Close/remove postings

    # Candidate Discovery & Evaluation
    SearchCandidatesTool(),           # Find candidates for opportunities
    EvaluateCandidateFitTool(),       # Detailed candidate assessment
    ShortlistCandidatesTool(),        # Manage candidate pools

    # Hiring Workflow
    ScheduleInterviewsTool(),         # Coordinate interviews
    SendOfferTool(),                  # Make job offers
    ManageHiringPipelineTool(),       # Track hiring progress
]
```

#### Admin-Focused Tools
```python
ADMIN_TOOLS = [
    # System Management
    ManageAllUsersTool(),             # User administration
    SystemAnalyticsTool(),            # Platform insights
    ContentModerationTool(),          # Review/manage all content

    # Full Access Tools (All candidate + employer tools)
    *CANDIDATE_TOOLS,
    *EMPLOYER_TOOLS,
]
```

### 2. Benefits of Purpose-Built Tools

#### **Clarity of Intent**
- `SubmitApplicationTool()` clearly indicates candidate workflow
- `CreateJobPostingTool()` clearly indicates employer responsibility
- No ambiguity about tool purpose or permissions

#### **Workflow Alignment**
- Tools match natural user workflows
- Each tool serves one clear purpose in the user's journey
- No conditional logic within tools

#### **Security by Design**
- Tools inherently respect focus boundaries
- `ManageMyProfileTool()` automatically knows it's for the current user
- `CreateJobPostingTool()` automatically assigns ownership to current employer

#### **Maintainability**
- Each tool has single responsibility
- Clear separation of concerns
- Easy to test and modify individual workflows

### 3. Tool Registry Implementation

#### **Focus-Based Loading**
```python
def get_tools_for_focus(user, focus: str) -> List[BaseTool]:
    """Load purpose-built tools for specific user focus"""

    if focus == 'candidate':
        return CANDIDATE_TOOLS
    elif focus == 'employer':
        return EMPLOYER_TOOLS
    elif focus == 'admin':
        return ADMIN_TOOLS
    else:
        return []  # No tools for unknown focus
```

#### **Tool Naming Convention**
```
# Candidate Tools: {action}_{target}_{context}
- manage_my_profile
- search_opportunities
- submit_application

# Employer Tools: {action}_{target}_{ownership}
- create_job_posting
- manage_my_postings
- evaluate_candidate_fit

# Admin Tools: {action}_{scope}_{target}
- manage_all_users
- system_analytics
```

### 4. API Layer Alignment

#### **Focus-Specific Endpoints** (Alternative to Unified APIs)
```
/api/candidate/
├── GET /profile/              # My profile only
├── PUT /profile/              # Update my profile
├── GET /opportunities/        # Available jobs
├── POST /applications/        # Submit applications

/api/employer/
├── POST /opportunities/       # Create job posting
├── GET /opportunities/        # My postings only
├── GET /candidates/           # Browse candidates
├── POST /applications/{id}/review/  # Review applications

/api/admin/
├── GET /users/                # All users
├── GET /analytics/            # System analytics
├── *                         # Full access
```

### 5. Agent Experience

#### **Context-Aware Conversations**
- **Candidate**: *"Help me find a job in data science"* → Uses `search_opportunities`
- **Employer**: *"Help me find candidates for my software engineer role"* → Uses `search_candidates`
- **Admin**: *"Show me system usage statistics"* → Uses `system_analytics`

#### **Workflow Guidance**
- Agent can guide users through their specific workflow
- Tools reinforce the correct user journey
- No confusion about available actions

## Implementation Strategy

### Phase 1: Tool Inventory & Design
- Audit current generic tools
- Design purpose-built replacements
- Define clear naming conventions

### Phase 2: Tool Development
- Implement focus-specific tools
- Update tool registry
- Maintain backward compatibility during transition

### Phase 3: API Alignment (Optional)
- Consider focus-specific API endpoints
- Update frontend to use appropriate endpoints
- Maintain unified APIs as fallback

### Phase 4: Testing & Migration
- Test each tool in its target focus context
- Gradual migration from generic to specific tools
- Validate user workflows remain intact

## Key Advantages

**User Experience:**
- Tools match user mental models
- Clear purpose and permissions
- Workflow-appropriate functionality

**Developer Experience:**
- Single responsibility principle
- Clear tool boundaries
- Easier testing and maintenance

**System Reliability:**
- No conditional logic in tools
- Predictable behavior per focus
- Built-in permission boundaries

## Trade-offs

**Code Duplication:** More tools = more code to maintain
**Migration Complexity:** Transitioning from generic to specific tools
**Flexibility:** Harder to add new focus types later

**Recommendation:** Accept the duplication trade-off for the clarity and reliability benefits. Focus-specific tools provide better user experience and system integrity.
