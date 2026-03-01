from enum import Enum
from dataclasses import dataclass
from typing import Optional


class VehicleState(Enum):
    ASLEEP = "ASLEEP"
    PARKED = "PARKED"
    DRIVING = "DRIVING"
    CHARGING = "CHARGING"


@dataclass
class VehicleStatus:
    vehicle_id: int
    state: VehicleState
    last_update: Optional[float] = None
