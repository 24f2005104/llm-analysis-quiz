from pydantic import BaseModel

class SolveRequest(BaseModel):
    email: str
    secret: str
    url: str
