"""Constants for the Marstek Battery System integration."""

DOMAIN = "marstek"

# Config flow
CONF_HOST = "host"
CONF_PORT = "port"

# Default values
DEFAULT_PORT = 30000
DEFAULT_NAME = "Marstek Battery System"

# Device models
DEVICE_VENUS_C = "VenusC"
DEVICE_VENUS_E = "VenusE"
DEVICE_VENUS_D = "VenusD"

# Operating modes
MODE_AUTO = "Auto"
MODE_AI = "AI"
MODE_MANUAL = "Manual"
MODE_PASSIVE = "Passive"

OPERATING_MODES = [MODE_AUTO, MODE_AI, MODE_MANUAL, MODE_PASSIVE]

# Attributes
ATTR_DEVICE_MODEL = "device_model"
ATTR_FIRMWARE_VERSION = "firmware_version"
ATTR_BLE_MAC = "ble_mac"
ATTR_WIFI_MAC = "wifi_mac"
