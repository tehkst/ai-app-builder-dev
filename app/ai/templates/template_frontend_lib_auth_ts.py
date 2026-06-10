from __future__ import annotations


TEMPLATE_PATH = 'frontend/lib/auth.ts'
TEMPLATE_CONTENT = 'export const ACCESS_TOKEN_KEY = "access_token";\n\nexport function saveAccessToken(token: string): void {\n  localStorage.setItem(ACCESS_TOKEN_KEY, token);\n}\n\nexport function getAccessToken(): string | null {\n  return localStorage.getItem(ACCESS_TOKEN_KEY);\n}\n\nexport function clearAccessToken(): void {\n  localStorage.removeItem(ACCESS_TOKEN_KEY);\n}\n\nexport function isAuthenticated(): boolean {\n  return Boolean(getAccessToken());\n}\n'
