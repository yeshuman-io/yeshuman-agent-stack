#!/usr/bin/env python
"""
Simple test script to verify basic API functionality.
"""
import requests
import json

BASE_URL = 'http://127.0.0.1:8000'

def test_health():
    """Test health endpoint."""
    try:
        response = requests.get(f'{BASE_URL}/api/health')
        if response.status_code == 200:
            print("✅ Health endpoint working")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False

def test_api_docs():
    """Test API docs endpoint."""
    try:
        response = requests.get(f'{BASE_URL}/api/docs')
        if response.status_code == 200:
            print("✅ API docs working")
            return True
        else:
            print(f"❌ API docs failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API docs error: {e}")
        return False

def test_auth_login():
    """Test auth login endpoint."""
    try:
        response = requests.post(
            f'{BASE_URL}/api/auth/login/',
            json={'username': 'daryl@yeshuman.io', 'password': 'abc'},
            headers={'Content-Type': 'application/json'}
        )
        print(f"Auth login response: {response.status_code}")
        if response.status_code == 200:
            print("✅ Auth login working")
            data = response.json()
            if 'token' in data:
                print("✅ Got JWT token")
                return data['token']
            else:
                print(f"❌ No token in response: {data}")
                return None
        else:
            print(f"❌ Auth login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Auth login error: {e}")
        return None

def main():
    """Run simple tests."""
    print("🔍 Running simple API tests...")

    # Test basic endpoints
    health_ok = test_health()
    docs_ok = test_api_docs()

    if not health_ok:
        print("❌ Server not responding properly")
        return

    # Test auth
    token = test_auth_login()

    if token:
        print("🎉 Basic auth working!")
    else:
        print("❌ Auth not working")

if __name__ == '__main__':
    main()

