# Employer Organisation Management - Implementation Summary

## 🎯 Core Requirements
- **PoC Focus**: Single organisation assumption (future multi-org support)
- **Access Control**: `/organisation` endpoints only available when employer group + employer focus
- **URLs**: Use slug-based URLs instead of IDs (e.g., `/employer/organisations/acme-corp`)
- **Recruiter Support**: Can create opportunities/ads on behalf of organisations
- **Avoid Complexity**: No advanced permissions/roles - focus on core features

## 🗄️ Database Changes
### Organisation Model
- Add `slug` field (unique, auto-generated from name)
- Add profile fields: `description`, `website`, `industry`
- Keep existing: `id`, `name`, `created_at`, `updated_at`

### User Model
- Add `managed_organisations` ManyToManyField (future-proof for multi-org)

## 🔗 API Endpoints
### Employer-Focused Organisation Management
```
GET    /api/employer/organisations/           # List user's managed orgs
POST   /api/employer/organisations/           # Create new org
GET    /api/employer/organisations/{slug}/    # Get org details
PUT    /api/employer/organisations/{slug}/    # Update org
```

### Opportunity Management
```
GET    /api/opportunities/employer/{org_slug}/    # List org opportunities
POST   /api/opportunities/employer/{org_slug}/    # Create opportunity
PUT    /api/opportunities/employer/{org_slug}/{opp_id}/    # Update opportunity
DELETE /api/opportunities/employer/{org_slug}/{opp_id}/    # Delete opportunity
```

## 🛠️ Agent Tools
### Organisation Management Tools
- `create_organisation` - Create new organisation
- `update_organisation` - Update organisation profile
- `get_organisation_details` - Get org info
- `list_user_organisations` - List user's managed orgs

### Opportunity Tools (Employer/Recruiter)
- `create_opportunity_for_organisation` - Create opp for specific org
- `update_organisation_opportunity` - Update existing opp
- `list_organisation_opportunities` - List org's opportunities

## 📡 UI Delta Update System
### Event Mappings
```python
TOOL_EVENT_MAPPINGS = {
    "create_organisation": {
        "entity": "organisation",
        "action": "created",
        "entity_id_extractor": lambda tool_call, result, user_id: extract_org_slug(result)
    },
    "update_organisation": {
        "entity": "organisation",
        "action": "updated",
        "entity_id_extractor": lambda tool_call, result, user_id: extract_org_slug(result)
    },
    "create_opportunity_for_organisation": {
        "entity": "opportunity",
        "action": "created",
        "entity_id_extractor": lambda tool_call, result, user_id: extract_opportunity_id(result)
    }
}
```

### Frontend Event Handlers
- Organisation events → Invalidate `employer-organisations` cache
- Organisation events → Invalidate `organisation/{slug}` cache
- Opportunity events → Invalidate `organisation-opportunities` cache

## 🎨 Frontend Updates
### Enhanced Employer Dashboard
- Show organisation management section when user has organisations
- Real-time updates via UI events
- Quick actions: "Create Organisation", "Manage {org}", "Post Job for {org}"

### Organisation Management Pages
```
/employer/organisations/{slug}           # Org dashboard
/employer/organisations/{slug}/edit      # Edit org profile
/employer/organisations/{slug}/opportunities/new    # Create opp
```

### Focus-Based Availability
- Organisation management only shows when: `employer group` AND `employer focus`
- Tools only available in employer focus context

## 📋 Implementation Phases

### Phase 1: Backend Foundation
1. **DB Models**: Add slug + profile fields to Organisation, user-org relationship
2. **API Routes**: Employer organisation CRUD endpoints
3. **Tools**: Organisation management tools with error handling
4. **UI Events**: Event mappings for all org operations
5. **Tool Composition**: Add org tools to employer composition

### Phase 2: Agent Integration
1. **Test Tools**: Verify org tools work with focus-based agent
2. **Test Events**: Verify UI events emit correctly
3. **Error Handling**: Test permission failures and edge cases

### Phase 3: Frontend Integration
1. **Event Handlers**: Add organisation event handling to SSE hook
2. **Dashboard**: Enhance employer dashboard with real-time org state
3. **Pages**: Create organisation management pages
4. **Testing**: End-to-end agent-driven org management

### Phase 4: Polish & Production
1. **Performance**: Optimise queries and caching
2. **UX**: Loading states, error messages, success feedback
3. **Docs**: Agent capabilities documentation

## 🔍 Key Technical Decisions

### Architecture Choices
- **Slug URLs**: Better SEO, user-friendly URLs
- **ManyToMany User-Orgs**: Future-proof for multi-org support
- **Employer-Only Endpoints**: Clean separation from general org APIs
- **UI Events**: Real-time updates without manual refresh

### Permission Model (PoC-Simple)
- **Employer Group + Employer Focus** = Organisation management access
- **Recruiter Group** = Can create opportunities for organisations
- **No Advanced Roles**: Owner/Admin/Member roles deferred to future

### Data Flow
1. User in employer focus → Agent gets org management tools
2. Agent creates organisation → Tool emits UI event
3. Frontend receives event → Invalidates org caches → UI updates instantly
4. User sees new organisation immediately

## 🎬 User Experience Flow

### Organisation Creation
```
User: "I want to set up my company profile"
Agent: Uses create_organisation tool
→ Organisation appears instantly in dashboard
→ User can immediately start posting jobs
```

### Opportunity Management
```
User: "Post a software engineer job for my company"
Agent: Uses create_opportunity_for_organisation tool
→ Opportunity appears in org's opportunity list
→ All views update in real-time
```

## ✅ Success Criteria

### Functional
- ✅ Employer focus shows organisation management
- ✅ Agent can create/update organisations
- ✅ Agent can create opportunities for organisations
- ✅ Recruiters can create opportunities
- ✅ Real-time UI updates work

### Technical
- ✅ Slug-based URLs work
- ✅ UI events emit and handle correctly
- ✅ Focus-based tool availability
- ✅ No permission complexity in PoC

### UX
- ✅ Seamless agent-UI integration
- ✅ Real-time updates feel natural
- ✅ Organisation management feels conversational

## 🚧 Future Extensions (Post-PoC)
- Multi-organisation support
- Team member management
- Organisation invitations
- Advanced permissions (owner/admin/member)
- Organisation analytics
- Recruiter organisation assignments
