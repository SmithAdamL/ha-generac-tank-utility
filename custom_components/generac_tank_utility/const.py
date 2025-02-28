DOMAIN = "generac_tank_utility"

# Configuration keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_DEVICES = "devices"          # List of tank devices (IDs and names)
# CONF_INTERVALS is no longer used.
CONF_ENABLE_MQTT = "enable_mqtt"  # Option to enable MQTT publishing (Coming Soon)

# Default settings
DEFAULT_SCAN_INTERVAL = 21600  # 6 hours (in seconds) as default polling interval per tank
DEFAULT_ENABLE_MQTT = False

# Thresholds for binary sensor alerts (in percentage)
LOW_FUEL_THRESHOLD = 20
LOW_BATTERY_THRESHOLD = 20
