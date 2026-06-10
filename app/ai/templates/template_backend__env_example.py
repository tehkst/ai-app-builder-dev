from __future__ import annotations


TEMPLATE_PATH = 'backend/.env.example'
TEMPLATE_CONTENT = 'APP_NAME=Generated Enterprise App\nDATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/generated_app\nJWT_SECRET_KEY=replace-with-secure-random-secret\nJWT_ALGORITHM=HS256\nACCESS_TOKEN_EXPIRE_MINUTES=60\nALLOWED_ORIGINS=["http://localhost:3000"]\n'
