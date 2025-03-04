"""climate for Homematic(IP) Local."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from hahomematic.const import HmPlatform
from hahomematic.devices.climate import BaseClimateEntity
import voluptuous as vol

from homeassistant.components.climate import ClimateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .control_unit import ControlUnit
from .generic_entity import HaHomematicGenericEntity

_LOGGER = logging.getLogger(__name__)

SERVICE_ENABLE_AWAY_MODE_BY_CALENDAR = "enable_away_mode_by_calendar"
SERVICE_ENABLE_AWAY_MODE_BY_DURATION = "enable_away_mode_by_duration"
SERVICE_DISABLE_AWAY_MODE = "disable_away_mode"
ATTR_AWAY_END = "end"
ATTR_AWAY_HOURS = "hours"
ATTR_AWAY_TEMPERATURE = "away_temperature"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Homematic(IP) Local climate platform."""
    control_unit: ControlUnit = hass.data[DOMAIN][config_entry.entry_id]

    @callback
    def async_add_climate(args: Any) -> None:
        """Add climate from Homematic(IP) Local."""
        entities: list[HaHomematicGenericEntity] = []

        for hm_entity in args:
            entities.append(HaHomematicClimate(control_unit, hm_entity))

        if entities:
            async_add_entities(entities)

    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            control_unit.async_signal_new_hm_entity(
                config_entry.entry_id, HmPlatform.CLIMATE
            ),
            async_add_climate,
        )
    )

    async_add_climate(
        control_unit.async_get_new_hm_entities_by_platform(HmPlatform.CLIMATE)
    )

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_ENABLE_AWAY_MODE_BY_CALENDAR,
        {
            vol.Required(ATTR_AWAY_END): cv.datetime,
            vol.Required(ATTR_AWAY_TEMPERATURE, default=18.0): vol.All(
                vol.Coerce(float), vol.Range(min=4.5, max=30.5)
            ),
        },
        "async_enable_away_mode_by_calendar",
    )
    platform.async_register_entity_service(
        SERVICE_ENABLE_AWAY_MODE_BY_DURATION,
        {
            vol.Required(ATTR_AWAY_HOURS): cv.positive_int,
            vol.Required(ATTR_AWAY_TEMPERATURE, default=18.0): vol.All(
                vol.Coerce(float), vol.Range(min=4.5, max=30.5)
            ),
        },
        "async_enable_away_mode_by_duration",
    )
    platform.async_register_entity_service(
        SERVICE_DISABLE_AWAY_MODE,
        {},
        "async_disable_away_mode",
    )


class HaHomematicClimate(HaHomematicGenericEntity[BaseClimateEntity], ClimateEntity):
    """Representation of the HomematicIP climate entity."""

    def __init__(
        self,
        control_unit: ControlUnit,
        hm_entity: BaseClimateEntity,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(control_unit=control_unit, hm_entity=hm_entity)
        self._attr_temperature_unit = hm_entity.temperature_unit
        self._attr_supported_features = hm_entity.supported_features
        self._attr_target_temperature_step = hm_entity.target_temperature_step
        self._attr_min_temp = float(hm_entity.min_temp)
        self._attr_max_temp = float(hm_entity.max_temp)

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._hm_entity.target_temperature

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._hm_entity.current_temperature

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self._hm_entity.current_humidity

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie."""
        return self._hm_entity.hvac_mode

    @property
    def hvac_modes(self) -> list[str]:
        """Return the list of available hvac operation modes."""
        return self._hm_entity.hvac_modes

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode."""
        return self._hm_entity.preset_mode

    @property
    def preset_modes(self) -> list[str]:
        """Return a list of available preset modes incl. hmip profiles."""
        return self._hm_entity.preset_modes

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        await self._hm_entity.set_temperature(**kwargs)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        await self._hm_entity.set_hvac_mode(hvac_mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        await self._hm_entity.set_preset_mode(preset_mode)

    async def async_enable_away_mode_by_calendar(
        self, end: datetime, away_temperature: float
    ) -> None:
        """Enable the away mode by calendar on thermostat."""
        start = datetime.now() - timedelta(minutes=10)
        await self._hm_entity.enable_away_mode_by_calendar(
            start=start, end=end, away_temperature=away_temperature
        )

    async def async_enable_away_mode_by_duration(
        self, hours: int, away_temperature: float
    ) -> None:
        """Enable the away mode by duration on thermostat."""
        await self._hm_entity.enable_away_mode_by_duration(
            hours=hours, away_temperature=away_temperature
        )

    async def async_disable_away_mode(self) -> None:
        """Disable the away mode on thermostat."""
        await self._hm_entity.disable_away_mode()
