from __future__ import annotations


TEMPLATE_PATH = 'backend/Dockerfile'
TEMPLATE_CONTENT = 'FROM python:3.11-slim\n\nWORKDIR /app\n\nENV PYTHONDONTWRITEBYTECODE=1\nENV PYTHONUNBUFFERED=1\n\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n\nCOPY . .\n\nEXPOSE 8000\n\nCMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]\n'
