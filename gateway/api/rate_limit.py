
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def _ip_real() -> str:

    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        ultima = forwarded.split(",")[-1].strip()
        if ultima:
            return ultima
    return get_remote_address()


limiter = Limiter(key_func=_ip_real)
