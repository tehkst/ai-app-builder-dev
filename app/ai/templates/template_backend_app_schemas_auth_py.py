from __future__ import annotations


TEMPLATE_PATH = 'backend/app/schemas/auth.py'
TEMPLATE_CONTENT = 'from pydantic import BaseModel, EmailStr\n\n\nclass UserRegisterRequest(BaseModel):\n    username: str\n    email: EmailStr\n    password: str\n\n\nclass UserLoginRequest(BaseModel):\n    username: str\n    password: str\n\n\nclass UserResponse(BaseModel):\n    access_token: str\n    token_type: str\n'
