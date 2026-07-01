"""
Shared Pydantic schemas — the request/response shapes that cross module
boundaries (FastAPI endpoints in main.py, and the return value of
debate.py's orchestration function).

Defining these once means main.py and debate.py both import the same
schema instead of each inventing a slightly different shape for "a debate
topic" or "the result of a debate."
"""

from pydantic import BaseModel


class DebateRequest(BaseModel):
    """What the frontend sends when starting a new debate."""

    topic: str


class DebateResult(BaseModel):
    """The full output of one debate, returned to the frontend."""

    topic: str
    for_argument: str
    against_argument: str
    verdict: str
