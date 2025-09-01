# Multi-Tenant Configuration Guide

This codebase supports multiple client configurations through environment variables. You can switch between different clients without duplicating code.

## Supported Clients

- **yeshuman** - Yes Human (default)
- **bookedai** - Booked AI (booking/scheduling)
- **talentco** - TalentCo (HR/recruitment)
- **lumie** - Lumie (lighting design)

## Backend Configuration

### Environment Variables

Create a `.env` file in the `/api` directory:

```bash
# Client Configuration
CLIENT_CONFIG=yeshuman  # Options: yeshuman, bookedai, talentco, lumie

# Django Configuration
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1,testserver

# Database Configuration
USE_POSTGRES=true
POSTGRES_DB=your-db-name
POSTGRES_USER=your-db-user
POSTGRES_PASSWORD=your-db-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
```

### Client-Specific Features

Each client has unique:
- **System Prompt** - AI personality and behavior
- **Branding** - Welcome messages, descriptions
- **Color Scheme** - Primary colors for UI theming

### Switching Clients

1. Set `CLIENT_CONFIG` in your `.env` file
2. Restart the Django server
3. The API will automatically use the new client's configuration

Example for Booked AI:
```bash
CLIENT_CONFIG=bookedai
```

## Frontend Configuration

### Environment Variables

Create a `.env` file in the `/labs` directory:

```bash
# Client Configuration
VITE_CLIENT_CONFIG=yeshuman  # Options: yeshuman, bookedai, talentco, lumie
```

### Client-Specific Features

Each client has:
- **Title Variations** - Animated title changes
- **Sarcastic Messages** - Context-appropriate responses
- **Welcome Messages** - Login form branding
- **Taglines** - Sidebar and UI descriptions

### Switching Frontend Clients

1. Set `VITE_CLIENT_CONFIG` in your `.env` file
2. Restart the Vite dev server
3. The UI will automatically update with new branding

## API Endpoints

### Get Current Configuration

```bash
GET /api/config
```

Returns the current client configuration including:
- Client name
- System prompt
- Branding information
- UI text

### Example Response

```json
{
  "client": "bookedai",
  "config": {
    "name": "Booked AI",
    "brand": "Booked AI",
    "primary_color": "#10b981",
    "system_prompt": "You are Booked AI...",
    "welcome_message": "Welcome to Booked AI.",
    "tagline": "Intelligent booking and scheduling"
  }
}
```

## Development Workflow

1. **Start with Default**: `CLIENT_CONFIG=yeshuman`
2. **Switch Clients**: Change environment variable and restart servers
3. **Test Each Client**: Verify branding, system prompts, and functionality
4. **Add New Clients**: Add configuration to `CLIENT_CONFIGS` in settings.py and constants/index.ts

## Adding New Clients

### Backend (settings.py)

Add to `CLIENT_CONFIGS`:

```python
'newclient': {
    'name': 'New Client',
    'brand': 'New Client',
    'logo_path': '/logos/newclient-logo.svg',
    'primary_color': '#your-color',
    'system_prompt': 'Your system prompt...',
    'welcome_message': 'Welcome to New Client.',
    'tagline': 'Your tagline here',
    'description': "Contact info for new client."
},
```

### Frontend (constants/index.ts)

Add to `CLIENT_CONFIGS`:

```typescript
newclient: {
  name: 'New Client',
  brand: 'New Client',
  logoPath: '/logos/newclient-logo.svg',
  primaryColor: '#your-color',
  welcomeMessage: 'Welcome to New Client.',
  tagline: 'Your tagline here',
  description: "Contact info for new client.",
  titleVariations: ['New Client', 'New Client!', ...],
  sarcasticVariations: ['Custom message 1', 'Custom message 2', ...],
},
```

## Benefits

✅ **Single Codebase** - No code duplication
✅ **Environment-Driven** - Easy switching via env vars
✅ **Consistent Architecture** - Same patterns across clients
✅ **Scalable** - Easy to add new clients
✅ **Maintainable** - Changes affect all clients automatically

## Deployment

For production deployment:
1. Set appropriate `CLIENT_CONFIG` in your deployment environment
2. Configure client-specific assets (logos, etc.)
3. Use the same codebase for all client deployments
