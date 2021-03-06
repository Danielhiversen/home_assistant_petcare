"""Constants for the Sure Petcare component."""
from datetime import timedelta

DOMAIN = "petcare"
DEFAULT_DEVICE_CLASS = "lock"

# sure petcare api
SURE_API_TIMEOUT = 60

# flap
BATTERY_ICON = "mdi:battery"
SURE_BATT_VOLTAGE_FULL = 1.6  # voltage
SURE_BATT_VOLTAGE_LOW = 1.25  # voltage
SURE_BATT_VOLTAGE_DIFF = SURE_BATT_VOLTAGE_FULL - SURE_BATT_VOLTAGE_LOW

# lock state service
SERVICE_SET_LOCK_STATE = "set_lock_state"
ATTR_FLAP_ID = "flap_id"
ATTR_LOCK_STATE = "lock_state"
