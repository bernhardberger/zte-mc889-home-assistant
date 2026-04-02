"""Constants for the ZTE MC889 integration."""

DOMAIN = "zte_mc889"

CONF_HOST = "host"
CONF_PASSWORD = "password"

DEFAULT_HOST = "192.168.254.1"
DEFAULT_SCAN_INTERVAL = 30

# All fields fetched from the modem each update cycle.
#
# NOTE: pm_sensor_mdm is intentionally excluded — it causes the modem
# to return {"result": "failure"} for the entire query on firmware
# BD_ATMC889V1.0.0B19.  pm_modem_5g works fine (returns empty when
# no data is available).
POLL_FIELDS = [
    # Signal
    "network_type", "network_provider", "signalbar",
    "Z5g_SINR", "Z5g_rsrp", "Z5g_rsrq",
    "nr5g_action_band", "nr5g_cell_id",
    "lte_rsrp", "lte_snr",
    # Traffic
    "realtime_rx_thrpt", "realtime_tx_thrpt",
    "monthly_rx_bytes", "monthly_tx_bytes",
    # Device
    "wan_ipaddr", "wa_inner_version", "mtu", "opms_wan_mode", "ppp_status",
    # Thermal
    "pm_modem_5g",
]
