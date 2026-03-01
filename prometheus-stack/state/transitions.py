from state.machine import VehicleState


# Simple allowed transitions map
ALLOWED_TRANSITIONS = {
    VehicleState.ASLEEP: {VehicleState.PARKED},
    VehicleState.PARKED: {VehicleState.DRIVING, VehicleState.CHARGING, VehicleState.ASLEEP},
    VehicleState.DRIVING: {VehicleState.PARKED},
    VehicleState.CHARGING: {VehicleState.PARKED},
}


def can_transition(from_state: VehicleState, to_state: VehicleState) -> bool:
    return to_state in ALLOWED_TRANSITIONS.get(from_state, set())
