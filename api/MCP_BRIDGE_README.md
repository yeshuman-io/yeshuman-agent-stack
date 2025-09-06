# MCP Bridge Setup for Yes Human Server

Since most MCP clients (Cursor, Claude Desktop) expect stdio communication, but our server uses HTTP, users need a bridge. Here are the standard open-source options:

## Option 1: @thefoot/mcp-stdio-http-bridge (Recommended)

**No Installation Required - Use pnpm dlx:**

```bash
pnpm dlx @thefoot/mcp-stdio-http-bridge --url http://127.0.0.1:8000/mcp/
```

**Cursor MCP Configuration:**
```json
{
  "mcpServers": {
    "yeshuman": {
      "command": "pnpm",
      "args": [
        "dlx",
        "@thefoot/mcp-stdio-http-bridge",
        "--url",
        "http://127.0.0.1:8000/mcp/"
      ]
    }
  }
}
```

**Alternative with npx:**
```bash
npx @thefoot/mcp-stdio-http-bridge --url http://127.0.0.1:8000/mcp/
```

## Option 2: syntax-syndicate/mcp-http-stdio-bridge

**No Installation Required - Use pnpm dlx:**

```bash
pnpm dlx mcp-http-stdio-bridge --http-url http://127.0.0.1:8000/mcp/
```

**Alternative with npx:**
```bash
npx mcp-http-stdio-bridge --http-url http://127.0.0.1:8000/mcp/
```

## Option 3: 54rt1n/mcpgate

**No Installation Required - Use pnpm dlx:**

```bash
pnpm dlx mcpgate --endpoint http://127.0.0.1:8000/mcp/
```

**Alternative with npx:**
```bash
npx mcpgate --endpoint http://127.0.0.1:8000/mcp/
```

## Option 4: Python-based Bridge (Custom)

If users prefer Python, they can use our custom bridge:

```bash
cd /path/to/yeshuman/api
python mcp_stdio_bridge.py
```

## For Production/Cloud Deployment

If you're deploying to Railway or other cloud platforms, you might want to:

1. **Use Railway's built-in MCP support** (if available)
2. **Create a separate stdio MCP server** for production
3. **Use a cloud-based bridge service**

## Quick Start for Users

1. **Start your Django MCP server:**
   ```bash
   cd /path/to/yeshuman/api
   source .venv/bin/activate
   python manage.py runserver 0.0.0.0:8000
   ```

2. **Use pnpm dlx (no installation needed):**
   ```bash
   pnpm dlx @thefoot/mcp-stdio-http-bridge --url http://127.0.0.1:8000/mcp/
   ```

3. **Configure Cursor MCP settings:**
   ```json
   {
     "mcpServers": {
       "yeshuman": {
         "command": "pnpm",
         "args": [
           "dlx",
           "@thefoot/mcp-stdio-http-bridge",
           "--url",
           "http://127.0.0.1:8000/mcp/"
         ]
       }
     }
   }
   ```

   **Alternative npx configuration:**
   ```json
   {
     "mcpServers": {
       "yeshuman": {
         "command": "npx",
         "args": ["@thefoot/mcp-stdio-http-bridge", "--url", "http://127.0.0.1:8000/mcp/"]
       }
     }
   }
   ```

4. **Restart Cursor** and the MCP server should be available.

## Troubleshooting

- **Bridge not connecting:** Ensure your Django server is running and accessible
- **CORS issues:** The bridge handles CORS automatically
- **Port conflicts:** Make sure port 8000 is available
- **Virtual environment:** Always activate your Python virtual environment

## Why This Approach?

- **Standard solution:** Uses established open-source tools
- **No custom code needed:** Users can install via npm/pnpm
- **Cross-platform:** Works on Windows, Mac, Linux
- **Active community:** These bridges are maintained and updated
- **Flexible:** Multiple options for different preferences
