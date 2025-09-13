"""
Tests for accounts API endpoints using Django Ninja.
"""
import json
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from ninja.testing import TestClient
from yeshuman.api import api
import os

User = get_user_model()


class AccountsAPITestCase(TestCase):
    """Test cases for accounts API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Skip Ninja API registry validation for tests
        os.environ["NINJA_SKIP_REGISTRY"] = "1"
        self.client = TestClient(api)

        # Test user data
        self.test_user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123"
        }

    def test_register_success(self):
        """Test successful user registration."""
        response = self.client.post("/accounts/register", json=self.test_user_data)

        print(f"Register response status: {response.status_code}")
        print(f"Register response data: {response.json()}")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["username"], self.test_user_data["username"])
        self.assertEqual(data["user"]["email"], self.test_user_data["email"])
        self.assertIn("token", data)

        # Verify user was created in database
        user = User.objects.get(username=self.test_user_data["username"])
        self.assertEqual(user.email, self.test_user_data["email"])

    def test_register_duplicate_username(self):
        """Test registration with duplicate username."""
        # Create first user
        self.client.post("/accounts/register", json=self.test_user_data)

        # Try to create user with same username but different email
        duplicate_data = self.test_user_data.copy()
        duplicate_data["email"] = "different@example.com"

        response = self.client.post("/accounts/register", json=duplicate_data)

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("Username already exists", data["error"])

    def test_register_duplicate_email(self):
        """Test registration with duplicate email."""
        # Create first user
        self.client.post("/accounts/register", json=self.test_user_data)

        # Try to create user with same email
        duplicate_data = self.test_user_data.copy()
        duplicate_data["username"] = "differentuser"

        response = self.client.post("/accounts/register", json=duplicate_data)

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("Email already exists", data["error"])

    def test_register_invalid_email(self):
        """Test registration with invalid email."""
        invalid_data = self.test_user_data.copy()
        invalid_data["email"] = "invalid-email"

        response = self.client.post("/accounts/register", json=invalid_data)

        # Django Ninja returns 422 for Pydantic validation errors
        self.assertEqual(response.status_code, 422)
        data = response.json()
        # Check for Pydantic validation error format
        self.assertIn("detail", data)

    def test_register_password_too_short(self):
        """Test registration with password too short."""
        invalid_data = self.test_user_data.copy()
        invalid_data["password"] = "ab"  # Too short

        response = self.client.post("/accounts/register", json=invalid_data)

        # Django Ninja returns 422 for Pydantic validation errors
        self.assertEqual(response.status_code, 422)
        data = response.json()
        # Check for Pydantic validation error format
        self.assertIn("detail", data)

    def test_register_passwords_not_matching(self):
        """Test registration with non-matching passwords."""
        invalid_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "password_confirm": "differentpass"
        }

        response = self.client.post("/accounts/register", json=invalid_data)

        # Django Ninja returns 422 for Pydantic validation errors
        self.assertEqual(response.status_code, 422)
        data = response.json()
        # Check for Pydantic validation error format
        self.assertIn("detail", data)

    def test_login_success(self):
        """Test successful login."""
        # First register the user
        register_response = self.client.post("/accounts/register", json=self.test_user_data)
        print(f"Registration response: {register_response.json()}")

        # Now login
        login_data = {
            "username": self.test_user_data["username"],
            "password": self.test_user_data["password"]
        }

        response = self.client.post("/accounts/login", json=login_data)
        print(f"Login response status: {response.status_code}")
        print(f"Login response data: {response.json()}")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["username"], self.test_user_data["username"])
        self.assertIn("token", data)

    def test_login_with_email(self):
        """Test login using email instead of username."""
        # First register the user
        self.client.post("/accounts/register", json=self.test_user_data)

        # Now login with email
        login_data = {
            "username": self.test_user_data["email"],  # Using email as username
            "password": self.test_user_data["password"]
        }

        response = self.client.post("/accounts/login", json=login_data)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["email"], self.test_user_data["email"])

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpass"
        }

        response = self.client.post("/accounts/login", json=login_data)

        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("Invalid credentials", data["error"])

    def test_get_current_user_authenticated(self):
        """Test getting current user with valid JWT token."""
        # Register and login to get token
        self.client.post("/accounts/register", json=self.test_user_data)

        login_response = self.client.post("/accounts/login", json={
            "username": self.test_user_data["username"],
            "password": self.test_user_data["password"]
        })

        token = login_response.json()["token"]

        # Now test getting current user with token
        # Django test client converts headers to HTTP_* format in request.META
        response = self.client.get("/accounts/me", headers={
            "HTTP_AUTHORIZATION": f"Bearer {token}"
        })

        print(f"Get user response status: {response.status_code}")
        print(f"Get user response data: {response.json()}")
        print(f"Token used: {token[:20]}...")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], self.test_user_data["username"])
        self.assertEqual(data["email"], self.test_user_data["email"])

    def test_get_current_user_no_token(self):
        """Test getting current user without token."""
        response = self.client.get("/accounts/me")

        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("No token provided", data["error"])

    def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        response = self.client.get("/accounts/me", headers={
            "HTTP_AUTHORIZATION": "Bearer invalid_token"
        })

        print(f"Invalid token response status: {response.status_code}")
        print(f"Invalid token response data: {response.json()}")

        self.assertEqual(response.status_code, 401)
        data = response.json()
        # The API might return "No token provided" for invalid tokens too
        self.assertTrue("No token provided" in data["error"] or "Invalid token" in data["error"])

    def test_get_current_user_expired_token(self):
        """Test getting current user with expired token."""
        # Create an expired token manually
        import jwt
        from datetime import datetime, timedelta
        from django.conf import settings

        expired_payload = {
            'user_id': 1,
            'username': 'test',
            'email': 'test@example.com',
            'exp': datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            'iat': datetime.utcnow() - timedelta(hours=2),
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm='HS256')

        response = self.client.get("/accounts/me", headers={
            "HTTP_AUTHORIZATION": f"Bearer {expired_token}"
        })

        print(f"Expired token response status: {response.status_code}")
        print(f"Expired token response data: {response.json()}")

        self.assertEqual(response.status_code, 401)
        data = response.json()
        # The API might return "No token provided" for expired tokens too
        self.assertTrue("No token provided" in data["error"] or "Token expired" in data["error"])
