from __future__ import annotations


TEMPLATE_PATH = 'frontend/lib/errors.ts'
TEMPLATE_CONTENT = 'export function getSafeErrorMessage(\n  fallbackMessage: string,\n): string {\n  return fallbackMessage;\n}\n\nexport const SAFE_ERROR_MESSAGES = {\n  loginFailed: "Login failed. Please check your credentials.",\n  registerFailed: "Registration failed. Please try again.",\n  customersLoadFailed: "Unable to load customers. Please try again later.",\n  customerCreateFailed: "Unable to create customer. Please try again later.",\n  unauthorized: "Your session has expired. Please log in again.",\n};\n'
