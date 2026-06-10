from __future__ import annotations


TEMPLATE_PATH = 'backend/app/core/rate_limit.py'
TEMPLATE_CONTENT = 'from slowapi import Limiter\nfrom slowapi import _rate_limit_exceeded_handler\nfrom slowapi.util import get_remote_address\n\n\nAUTH_RATE_LIMIT = "10/minute"\n\n\nlimiter = Limiter(\n    key_func=get_remote_address,\n)\n\n\nasync def rate_limit_exceeded_handler(request, exc):\n    return _rate_limit_exceeded_handler(request, exc)\n'
