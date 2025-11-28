from pydantic import BaseModel
from typing import Optional

class SolveResponse(BaseModel):
    status: str
    correct: Optional[bool] = None
    next_url: Optional[str] = None
    reason: Optional[str] = None
