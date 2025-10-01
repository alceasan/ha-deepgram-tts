# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-01-10

### Fixed

- **Critical Bug Fix**: Resolved 400 Bad Request errors when using streaming TTS by adding validation to ensure model parameters are never empty
- **Voice Configuration**: Fixed streaming TTS to use the same voice selection logic as regular TTS, ensuring configured voices are respected in both modes
- **Integration Setup**: Fixed platform setup issues that were preventing proper integration loading
- **Import Error**: Removed incorrect Platform import that was causing integration configuration failures

### Added

- **Debug Logging**: Added comprehensive debug logging in streaming TTS to help troubleshoot voice selection issues
- **Input Validation**: Added multiple layers of validation to prevent empty voice/model parameters from reaching the API

### Technical Details

- **API Layer**: Enhanced `async_synthesize_speech()` with model parameter validation
- **TTS Entity**: Updated both `async_get_tts_audio()` and `async_stream_tts_audio()` methods with consistent voice selection logic
- **Integration Setup**: Fixed platform forwarding in `__init__.py` to use proper async/await pattern
- **Error Prevention**: Added fallback mechanisms to ensure TTS requests always have valid voice parameters

## [1.0.0] - 2025-08-04

### Added

- Initial release of Deepgram TTS integration
- Support for Deepgram Aura-2 text-to-speech models
- Streaming TTS support for Home Assistant 2025.7+
- Voice and language selection
- HACS compatibility
- UI-based configuration (config flow)
