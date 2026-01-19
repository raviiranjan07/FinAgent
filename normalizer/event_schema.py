# Event Schema Normalizerfrom pydantic import BaseModel

class Event(BaseModel):
    event_id: str
    source: str
    title: str
    published_at: str
    raw_text: str
