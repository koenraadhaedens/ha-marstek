"""Constants for the Marstek integration."""

DOMAIN = "marstek"
DEFAULT_NAME = "Marstek Device"
DEFAULT_UPDATE_INTERVAL = 30

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_UPDATE_INTERVAL = "update_interval"

# Default UDP port for Marstek API
DEFAULT_UDP_PORT = 30000

# Device models
SUPPORTED_MODELS = ["Venus C", "Venus E", "Venus D"]

# API command IDs (for JSON-RPC)
API_COMMAND_ID = 1
