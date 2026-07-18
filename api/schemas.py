from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    location: str = Field(default="Chile", max_length=100)
    remote_only: bool = False
    filters: dict | None = None

class RegisterRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=20)

class ApplyRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000, pattern=r"^https?://")

class ModelRequest(BaseModel):
    model_id: str = Field(min_length=1, max_length=100)

class BatchApplyRequest(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=20)
    limit: int = Field(default=50, ge=1, le=500)
