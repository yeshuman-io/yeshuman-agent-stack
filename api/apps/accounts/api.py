"""
Authentication API using Django Ninja with JWT.
"""
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from ninja import Router, Schema
from typing import Optional
from pydantic import field_validator

# Create router for auth endpoints
auth_router = Router()

# JWT settings
JWT_SECRET_KEY = settings.SECRET_KEY
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = timedelta(hours=24)


class RegisterSchema(Schema):
    """Schema for user registration."""
    username: str
    email: str
    password: str
    password_confirm: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 3:
            raise ValueError('Password must be at least 3 characters long')
        return v

    @field_validator('password_confirm')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        try:
            validate_email(v)
        except ValidationError:
            raise ValueError('Invalid email format')
        return v


class UserResponse(Schema):
    """Response schema for user data."""
    id: int
    username: str
    email: str


class LoginSchema(Schema):
    """Schema for user login."""
    username: str
    password: str


def create_jwt_token(user):
    """Create JWT token for user."""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'exp': datetime.utcnow() + JWT_EXPIRATION_DELTA,
        'iat': datetime.utcnow(),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


@auth_router.post("/register", response={200: dict, 400: dict})
def register(request, data: RegisterSchema):
    """Register a new user."""
    try:
        User = get_user_model()
        # Check if user already exists
        if User.objects.filter(username=data.username).exists():
            return 400, {"error": "Username already exists"}

        if User.objects.filter(email=data.email).exists():
            return 400, {"error": "Email already exists"}

        # Create user
        user = User.objects.create_user(
            username=data.username,
            email=data.email,
            password=data.password
        )

        # Create JWT token
        token = create_jwt_token(user)

        return 200, {
            "success": True,
            "message": "User registered successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "token": token
        }

    except Exception as e:
        return 400, {"error": str(e)}


@auth_router.post("/login", response={200: dict, 401: dict})
def login(request, data: LoginSchema):
    """Login endpoint that returns JWT token."""
    # Try to authenticate with username first, then try with email
    user = authenticate(username=data.username, password=data.password)

    # If username authentication fails, try email authentication
    if user is None:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_obj = User.objects.get(email=data.username)
            user = authenticate(username=user_obj.username, password=data.password)
        except User.DoesNotExist:
            pass

    if user is None:
        return 401, {"error": "Invalid credentials"}

    # Create JWT token
    token = create_jwt_token(user)

    return 200, {
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        },
        "token": token
    }


@auth_router.get("/me", response={200: UserResponse, 401: dict})
def get_current_user(request):
    """Get current authenticated user information."""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth_header.startswith('Bearer '):
        return 401, {"error": "No token provided"}

    token = auth_header.split(' ')[1]

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        User = get_user_model()
        user = User.objects.get(id=payload['user_id'])

        return 200, UserResponse(
            id=user.id,
            username=user.username,
            email=user.email
        )
    except jwt.ExpiredSignatureError:
        return 401, {"error": "Token expired"}
    except jwt.InvalidTokenError:
        return 401, {"error": "Invalid token"}
    except User.DoesNotExist:
        return 401, {"error": "User not found"}
