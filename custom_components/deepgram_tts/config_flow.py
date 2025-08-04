"""Config flow for Deepgram TTS."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.core import callback
from slugify import slugify

from .api import (
    DeepgramTTSApiClient,
    DeepgramTTSApiClientAuthenticationError,
    DeepgramTTSApiClientCommunicationError,
    DeepgramTTSApiClientError,
)
from .api_models import DeepgramModelsClient
from .const import DOMAIN, LOGGER


class DeepgramTTSFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Deepgram TTS."""

    VERSION = 1

    @classmethod
    def async_get_options_flow(cls, config_entry):
        return DeepgramTTSOptionsFlowHandler(config_entry)

    async def async_step_connection_test(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Test connection to Deepgram public models endpoint before asking for API key."""
        _errors = {}
        if user_input is not None:
            # Intentar recuperar modelos sin API key
            try:
                session = async_create_clientsession(self.hass)
                models_client = DeepgramModelsClient(session)
                await models_client.fetch_models()
            except Exception as exc:
                LOGGER.error(f"Connection test failed: {exc}")
                _errors["base"] = "connection"
            else:
                # Si la conexión es exitosa, pasar al siguiente paso
                return await self.async_step_user()
        return self.async_show_form(
            step_id="connection_test",
            description_placeholders={"info": "Test connection to Deepgram public models endpoint."},
            data_schema=vol.Schema({}),
            errors=_errors,
        )

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            # Normaliza la clave para asegurar que siempre se almacene como CONF_API_KEY
            if "api_key" in user_input and CONF_API_KEY not in user_input:
                user_input[CONF_API_KEY] = user_input["api_key"]
            try:
                await self._test_credentials(
                    api_key=user_input[CONF_API_KEY],
                )
                # Fetch models for voice and language options
                session = async_create_clientsession(self.hass)
                models_client = DeepgramModelsClient(session)
                models_data = await models_client.fetch_models()
                self._models = models_data.get("tts", [])
            except DeepgramTTSApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except DeepgramTTSApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except DeepgramTTSApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                # Solo se permite una entrada de configuración para Deepgram TTS
                await self.async_set_unique_id("deepgram_tts")
                self._abort_if_unique_id_configured()
                # Elimina la clave antigua si existe y almacena solo CONF_API_KEY
                if "api_key" in user_input and CONF_API_KEY != "api_key":
                    del user_input["api_key"]
                # Guarda la clave API en self.context para el siguiente paso
                self.context["api_key"] = user_input[CONF_API_KEY]
                # Proceed to next step to select voice and language
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_KEY,
                        default=(user_input or {}).get(CONF_API_KEY, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    async def async_step_options(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle voice and language selection."""
        if user_input is not None:
            # Save selected options and create entry
            data = dict(user_input)
            # Recupera la clave API guardada en self.context y la añade a entry.data
            api_key = self.context.get("api_key")
            if api_key:
                data[CONF_API_KEY] = api_key
            return self.async_create_entry(title="Deepgram TTS", data=data)

        # Prepare options for voices and languages from fetched models
        voices = []
        languages = set()
        for model in getattr(self, "_models", []):
            voices.append((model["canonical_name"], model["name"]))
            for lang in model.get("languages", []):
                languages.add(lang)

        language_options = sorted(languages)
        voice_options = sorted(voices, key=lambda x: x[1])

        data_schema = vol.Schema(
            {
                vol.Required("language", default=language_options[0] if language_options else None): vol.In(language_options),
                vol.Required("voice", default=voice_options[0][0] if voice_options else None): vol.In([v[0] for v in voice_options]),
            }
        )

        return self.async_show_form(
            step_id="options",
            data_schema=data_schema,
        )

    async def _test_credentials(self, api_key: str) -> None:
        """Validate API key."""
        client = DeepgramTTSApiClient(
            api_key=api_key,
            session=async_create_clientsession(self.hass),
        )
        await client.async_test_api_key()


class DeepgramTTSOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for Deepgram TTS."""

    def __init__(self, config_entry):
        pass

    async def async_step_init(self, user_input=None):
        """Primer paso: seleccionar idioma base."""
        # Obtener valores actuales de options o data
        current_language = self.config_entry.options.get("language", self.config_entry.data.get("language", "en"))

        # Obtener modelos para mostrar idiomas base únicos
        session = async_create_clientsession(self.hass)
        models_client = DeepgramModelsClient(session)
        models_data = await models_client.fetch_models()
        languages = set()
        for model in models_data.get("tts", []):
            for lang in model.get("languages", []):
                base = lang.split("_")[0]
                languages.add(base)
        language_options = sorted(languages)

        if user_input is not None and "language" in user_input:
            # Guardar idioma seleccionado y pasar al siguiente paso
            self._selected_language = user_input["language"]
            return await self.async_step_voice()

        data_schema = vol.Schema(
            {
                vol.Required("language", default=current_language.split("_")[0] if "_" in current_language else current_language): vol.In(language_options),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )

    async def async_step_voice(self, user_input=None):
        """Segundo paso: seleccionar voz según idioma base."""
        # Recuperar idioma base seleccionado
        selected_language = getattr(self, "_selected_language", None)
        if not selected_language:
            # Si no hay idioma, volver al paso anterior
            return await self.async_step_init()

        # Obtener modelos para mostrar voces del idioma base seleccionado
        session = async_create_clientsession(self.hass)
        models_client = DeepgramModelsClient(session)
        models_data = await models_client.fetch_models()
        voices = []
        def matches(lang_code):
            return lang_code.split("_")[0] == selected_language
        for model in models_data.get("tts", []):
            if any(matches(lang) for lang in model.get("languages", [])):
                voices.append((model["canonical_name"], model["name"]))
        voice_options = sorted(voices, key=lambda x: x[1])

        # Valor actual o por defecto
        current_voice = self.config_entry.options.get("voice", self.config_entry.data.get("voice", voice_options[0][0] if voice_options else ""))

        if user_input is not None and "voice" in user_input:
            # Guardar idioma y voz seleccionados
            return self.async_create_entry(
                title="",
                data={
                    "language": selected_language,
                    "voice": user_input["voice"],
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required("voice", default=current_voice): vol.In([v[0] for v in voice_options]),
            }
        )

        return self.async_show_form(
            step_id="voice",
            data_schema=data_schema,
        )
