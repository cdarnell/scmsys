from pydantic import BaseModel
from typing import Optional


class Vehicle(BaseModel):
    id: int
    vin: Optional[str]
    display_name: Optional[str]
    state: Optional[str]
