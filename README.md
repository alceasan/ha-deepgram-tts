# Deepgram TTS - Home Assistant Custom Integration

![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)

Custom Home Assistant integration to use Deepgram as a text-to-speech (TTS) platform.

**Note:** You need a Deepgram account and API key to use this integration. You can sign up for a free account and get an API key for testing at [https://deepgram.com/](https://deepgram.com/).

## Features

- Synthesizes text to speech using Deepgram Aura-2 model: [https://deepgram.com/product/text-to-speech](https://deepgram.com/product/text-to-speech)
- Supports the new TTS streaming model introduced in Home Assistant 2025.7, reducing wait times for long conversational responses.
- Supports voice and language selection.
- Compatible with the standard Home Assistant `tts.speak` service.
- Allows per-service custom voice selection.
- UI-based configuration (config flow).
- HACS compatible.
- You can try out the available languages and voices in the [Deepgram Playground](https://playground.deepgram.com/?endpoint=speak&architecture=aura-2).

## Installation

### Using HACS

1. Add this repository (`alceasan/ha-deemgram-tts`) to HACS as a custom repository.
2. Install the `Deepgram TTS` integration.
3. Restart Home Assistant.
4. Go to Settings > Devices & Services > Add Integration and search for "Deepgram TTS".

### Manual

1. Copy the `custom_components/deepgram_tts` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration from the UI.

## Configuration

- The integration is fully configured via the Home Assistant UI.
- **A Deepgram API key is required.** You can get one for free testing by creating an account at [https://deepgram.com/](https://deepgram.com/).

[![Open your Home Assistant instance and show an integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=deepgram_tts)

## Usage

- Use the `tts.speak` service and select `Deepgram TTS` as the entity.
- You can pass the `voice` parameter to use a different voice than the default.

[![Open your Home Assistant instance and show your service developer tools with a specific action selected.](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=tts.speak)

```yaml
service: tts.speak
data:
  entity_id: tts.deepgram_tts
  message: "Hello, this is a test"
  voice: "aura-2-thalia-en"
```

## Development

- Requires Python 3.11+ and Home Assistant Core.
- Use the devcontainer for development in VSCode.
- Run `pip install -r requirements.txt` to install development dependencies.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT. See [LICENSE](LICENSE).

---

This project is not affiliated with or endorsed by Deepgram or Home Assistant.
