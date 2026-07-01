"""
Simple password gate for the app.

This isn't a full authentication system (no user accounts, no sessions,
no tokens) — it's a single shared secret that every request must include,
purely to stop random internet traffic from hitting our API-cost-incurring
endpoints. See config.py for where APP_PASSWORD comes from.
"""

import secrets

from fastapi import Header, HTTPException

from config import settings


async def verify_password(x_app_password: str = Header(...)) -> None:
    """
    FastAPI dependency that checks the X-App-Password request header
    against our configured password. Attach to any route that should be
    gated with Depends(verify_password).

    Uses secrets.compare_digest instead of `==` for the comparison. A
    plain `==` on strings stops as soon as it finds the first mismatched
    character, so a careful attacker could measure tiny timing
    differences to guess the password one character at a time.
    compare_digest always takes the same amount of time no matter where
    (or whether) the strings differ, so there's no timing signal to read.
    """
    if not secrets.compare_digest(x_app_password, settings.app_password):
        raise HTTPException(status_code=401, detail="Invalid password")
