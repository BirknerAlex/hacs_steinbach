"""Constants for the Steinbach Pool integration."""

DOMAIN = "steinbach"

MANUFACTURER = "Steinbach"

CONF_ACCESS_ID = "access_id"
CONF_ACCESS_SECRET = "access_secret"
CONF_REGION = "region"

# Tuya OpenAPI data-center endpoints, keyed by the region the user picked when
# creating their Tuya IoT cloud project.
TUYA_ENDPOINTS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}
DEFAULT_REGION = "eu"

DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 3600

# Device-point codes that the climate entity owns; they are not exposed as
# standalone sensors.
CLIMATE_CODES = frozenset(
    {"switch", "mode", "temp_set", "temp_current", "temp_unit_convert"}
)

# Device-point code carrying the fault bitmap.
FAULT_CODE = "fault"
