"""Sensor platform for ZTE MC889 integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZteMC889Coordinator
from .zte_api import signal_quality

# Map raw modem PPP status strings to human-readable labels
PPP_STATUS_MAP: dict[str, str] = {
    "ppp_connected": "Connected",
    "ppp_disconnected": "Disconnected",
    "ppp_connecting": "Connecting",
    "ppp_disconnecting": "Disconnecting",
    "ppp_idle": "Idle",
    "ppp_dial": "Dialing",
}


@dataclass(frozen=True, kw_only=True)
class ZteMC889SensorDescription(SensorEntityDescription):
    """Extended sensor description with value conversion hint."""

    is_numeric: bool = False
    is_hex_id: bool = False


SENSOR_DESCRIPTIONS: tuple[ZteMC889SensorDescription, ...] = (
    # ── Signal (enabled by default) ─────────────────────────────────────
    ZteMC889SensorDescription(
        key="signalbar",
        name="Signal bars",
        icon="mdi:signal-cellular-3",
        state_class=SensorStateClass.MEASUREMENT,
        is_numeric=True,
    ),
    ZteMC889SensorDescription(
        key="network_type",
        name="Network type",
        icon="mdi:antenna",
    ),
    ZteMC889SensorDescription(
        key="Z5g_rsrp",
        name="5G RSRP",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        is_numeric=True,
    ),
    ZteMC889SensorDescription(
        key="Z5g_SINR",
        name="5G SINR",
        icon="mdi:signal",
        native_unit_of_measurement="dB",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        is_numeric=True,
    ),
    # ── Traffic (enabled by default) ────────────────────────────────────
    ZteMC889SensorDescription(
        key="realtime_rx_thrpt",
        name="Download speed",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        is_numeric=True,
    ),
    ZteMC889SensorDescription(
        key="realtime_tx_thrpt",
        name="Upload speed",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        is_numeric=True,
    ),
    ZteMC889SensorDescription(
        key="monthly_rx_bytes",
        name="Monthly download",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        is_numeric=True,
    ),
    ZteMC889SensorDescription(
        key="monthly_tx_bytes",
        name="Monthly upload",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        is_numeric=True,
    ),
    # ── Signal (disabled by default) ────────────────────────────────────
    ZteMC889SensorDescription(
        key="network_provider",
        name="Provider",
        icon="mdi:sim",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    ZteMC889SensorDescription(
        key="Z5g_rsrq",
        name="5G RSRQ",
        icon="mdi:signal",
        native_unit_of_measurement="dB",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
        is_numeric=True,
    ),
    ZteMC889SensorDescription(
        key="nr5g_action_band",
        name="5G band",
        icon="mdi:radio-tower",
        entity_registry_enabled_default=False,
    ),
    ZteMC889SensorDescription(
        key="nr5g_cell_id",
        name="Cell ID",
        icon="mdi:radio-tower",
        entity_registry_enabled_default=False,
        is_hex_id=True,
    ),
    ZteMC889SensorDescription(
        key="lte_rsrp",
        name="LTE RSRP",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        is_numeric=True,
    ),
    ZteMC889SensorDescription(
        key="lte_snr",
        name="LTE SNR",
        icon="mdi:signal",
        native_unit_of_measurement="dB",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        is_numeric=True,
    ),
    # ── Device (diagnostic) ─────────────────────────────────────────────
    ZteMC889SensorDescription(
        key="wan_ipaddr",
        name="WAN IP",
        icon="mdi:ip",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ZteMC889SensorDescription(
        key="wa_inner_version",
        name="Firmware",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    ZteMC889SensorDescription(
        key="mtu",
        name="MTU",
        icon="mdi:resize",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_numeric=True,
    ),
    ZteMC889SensorDescription(
        key="opms_wan_mode",
        name="WAN mode",
        icon="mdi:lan",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    ZteMC889SensorDescription(
        key="ppp_status",
        name="Connection status",
        icon="mdi:lan-connect",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # ── Thermal (diagnostic) ────────────────────────────────────────────
    # NOTE: pm_sensor_mdm excluded — unsupported on firmware B19, crashes queries
    ZteMC889SensorDescription(
        key="pm_modem_5g",
        name="5G temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        is_numeric=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ZTE MC889 sensors from a config entry."""
    coordinator: ZteMC889Coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        ZteMC889Sensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    )


class ZteMC889Sensor(CoordinatorEntity[ZteMC889Coordinator], SensorEntity):
    """A sensor for a single ZTE MC889 data field."""

    _attr_has_entity_name = True
    entity_description: ZteMC889SensorDescription

    def __init__(
        self,
        coordinator: ZteMC889Coordinator,
        description: ZteMC889SensorDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        fw = None
        if self.coordinator.data:
            fw = self.coordinator.data.get("wa_inner_version")
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name="ZTE MC889",
            manufacturer="ZTE",
            model="MC889",
            sw_version=fw,
            configuration_url=f"https://{self.coordinator.host}",
        )

    @property
    def native_value(self) -> float | str | None:
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get(self.entity_description.key)
        if not value or value == "":
            return None

        desc = self.entity_description

        # Convert hex cell ID to decimal
        if desc.is_hex_id:
            try:
                return str(int(value, 16))
            except (ValueError, TypeError):
                return value

        # Convert numeric values
        if desc.is_numeric:
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        # Map PPP status to human-readable string
        if desc.key == "ppp_status":
            return PPP_STATUS_MAP.get(value, value)

        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Add signal quality rating as an attribute on signal sensors."""
        if not self.coordinator.data:
            return None
        key = self.entity_description.key
        if key in ("Z5g_rsrp", "Z5g_SINR", "Z5g_rsrq", "lte_rsrp", "lte_snr"):
            value = self.coordinator.data.get(key, "")
            quality = signal_quality(key, value)
            if quality:
                return {"quality": quality}
        return None
