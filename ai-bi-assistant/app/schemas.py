from pydantic import BaseModel, Field

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500, description="A sales analytics question")

class AskResponse(BaseModel):
    question: str
    intent: str
    answer: str
    result: dict | list
    supporting_data: dict | list
    query_method: str
    assumptions: list[str]
    warnings: list[str]
