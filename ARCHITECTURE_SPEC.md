# YesHuman Agent Stack - Architecture Specification

## Current State Assessment

### Existing Structure
```
api/
├── clients/duffel/client.py
├── schemas/travel/flights.py
├── services/travel/flight_service.py
├── tools/travel/flight_search.py
├── agent/graph.py
└── shared/...
```

### Issues Found
1. **Schema field inconsistencies** - `FlightOffer` missing required fields
2. **Transformer implementation gaps** - Methods reference non-existent fields
3. **Service layer issues** - Missing transformation methods
4. **Mixed architecture patterns** - Old domain structure alongside new structure

### Client Configuration (settings.py)
```python
CLIENT_CONFIGS = {
    'yeshuman': {'name': 'Yes Human', 'system_prompt': '...'},
    'bookedai': {'name': 'Booked AI', 'system_prompt': '...'},
    'talentco': {'name': 'TalentCo', 'system_prompt': '...'},
    'lumie': {'name': 'Lumie', 'system_prompt': '...'},
}
```

## Questions for Architecture Direction

### 1. Client Differentiation
What are the key differences between your 4 clients?

**Business Focus:**
- **Yes Human**: Full platform experience
- **Booked AI**: Travel/booking focused
- **TalentCo**: Talent/recruitment focused
- **Lumie**: Lighting/events focused

**Functional Differences:**
- Which APIs does each client need?
- What features are unique to each client?
- How does the agent behavior differ?

### 2. Organizational Approach
What makes most sense for organizing the codebase?

**Option A: Domain-Based (Simple)**
```
api/
├── clients/{provider}/client.py
├── schemas/{domain}/{entity}.py
├── services/{domain}/{entity}_service.py
├── tools/{domain}/{entity}_tool.py
```

**Option B: Feature-Based**
```
api/
├── clients/{provider}/client.py
├── features/{feature_name}/
│   ├── schemas/
│   ├── services/
│   └── tools/
```

**Option C: Service-Based**
```
api/
├── clients/{provider}/client.py
├── services/{service_name}/
│   ├── schemas/
│   ├── logic/
│   └── tools/
```

### 3. Client-Specific Logic
How do you want to handle client-specific behavior?

**Option A: Runtime Checks**
```python
if settings.CURRENT_CLIENT['name'] == 'Booked AI':
    # Business travel logic
```

**Option B: Feature Flags**
```python
if has_feature('premium_booking'):
    # Premium booking logic
```

**Option C: Strategy Pattern**
```python
strategy = get_client_strategy()
result = strategy.process_booking(booking_data)
```

## Immediate Action Plan

### Phase 1: Fix Current Issues
1. ✅ Fix schema field definitions
2. ✅ Complete transformer implementations
3. ✅ Add missing service methods
4. ✅ Clean up imports and registrations

### Phase 2: Establish Client Runtime Detection
```python
# api/shared/client.py
from django.conf import settings

def get_current_client():
    return settings.CURRENT_CLIENT

def get_client_name():
    return settings.CURRENT_CLIENT['name']

def has_feature(feature_name):
    """Check if current client has feature"""
    return feature_name in settings.CURRENT_CLIENT.get('features', [])
```

### Phase 3: Choose Architecture Pattern
Based on your answers to the questions above, we'll implement the right organizational approach.

## Your Input Needed

**Let's discuss:**

1. **What are the main functional areas** your platform needs to handle?
2. **What specific features/capabilities** differ between your 4 clients?
3. **What organizational approach** makes most sense for your use case?
4. **What's most important** to get working first?

Once we understand these fundamentals, we can design the right architecture pattern.