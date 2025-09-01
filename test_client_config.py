#!/usr/bin/env python3
"""
Test script to verify multi-tenant configuration switching.
Run this to test different client configurations.
"""

import os
import sys
import subprocess
from pathlib import Path

# Test different client configurations
test_configs = ['yeshuman', 'bookedai', 'talentco', 'lumie']

print("🔧 Testing Multi-Tenant Configuration Switching")
print("=" * 50)

for client in test_configs:
    print(f"\n📋 Testing client: {client}")

    try:
        # Run a separate Python process for each client config
        result = subprocess.run([
            sys.executable, '-c',
            f"""
import os
import sys
import django
from pathlib import Path

# Set client config before Django loads
os.environ['CLIENT_CONFIG'] = '{client}'

# Add the api directory to Python path
api_dir = Path('{Path(__file__).parent / 'api'}')
sys.path.insert(0, str(api_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yeshuman.settings')
django.setup()

from django.conf import settings

print(f"✅ Client: {{settings.CLIENT_CONFIG}}")
print(f"🏷️  Brand: {{settings.CURRENT_CLIENT['brand']}}")
print(f"🎨 Primary Color: {{settings.CURRENT_CLIENT['primary_color']}}")
print(f"💬 Welcome: {{settings.CURRENT_CLIENT['welcome_message']}}")
print(f"📝 System Prompt (first 100 chars): {{settings.CURRENT_CLIENT['system_prompt'][:100]}}...")
"""
        ], capture_output=True, text=True, cwd=Path(__file__).parent)

        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print(f"❌ Error with {client}:")
            print(result.stderr.strip())

    except Exception as e:
        print(f"❌ Error with {client}: {e}")

print("\n" + "=" * 50)
print("🎉 Multi-tenant configuration test completed!")
print("\nTo switch clients in production:")
print("1. Set CLIENT_CONFIG in your .env file")
print("2. Restart the Django server")
print("3. The system will automatically use the new client configuration")
