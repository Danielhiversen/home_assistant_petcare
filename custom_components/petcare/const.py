"""Constants for the Sure Petcare component."""

DOMAIN = "petcare"
DEFAULT_DEVICE_CLASS = "lock"

# sure petcare api
SURE_API_TIMEOUT = 60

# flap
BATTERY_ICON = "mdi:battery"
SURE_BATT_VOLTAGE_FULL = 1.6  # voltage
SURE_BATT_VOLTAGE_LOW = 1.25  # voltage
SURE_BATT_VOLTAGE_DIFF = SURE_BATT_VOLTAGE_FULL - SURE_BATT_VOLTAGE_LOW
