from slowapi import Limiter
from slowapi.util import get_remote_address


DEFAULT_RATE_LIMIT = "120/minute"
PLATFORM_API_RATE_LIMIT = "60/minute"
AUTH_API_RATE_LIMIT = "10/minute"


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[DEFAULT_RATE_LIMIT],
)
