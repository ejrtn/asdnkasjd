from pydantic import BaseModel, ConfigDict


class LatestDayUploadsResponse(BaseModel):
    status: str
    content: dict

    model_config = ConfigDict(from_attributes=True)
