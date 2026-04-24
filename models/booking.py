from pydantic import BaseModel

class BookingRequest(BaseModel):
    name: str
    phone: str
    date: str
    time: str