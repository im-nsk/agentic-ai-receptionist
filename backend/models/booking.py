from pydantic import BaseModel, Field

class BookingRequest(BaseModel):
    client_id: str
    name: str = Field(..., min_length=2)
    phone: str
    date: str
    time: str