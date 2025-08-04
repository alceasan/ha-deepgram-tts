from __future__ import annotations

import asyncio
import re
import logging
import io
from typing import AsyncIterable, AsyncGenerator

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

_LOGGER = logging.getLogger(__name__)

TRIM_MS_FROM_END = 100
SYNTHESIS_DELAY_S = 0.1

def remove_incompatible_characters(text: str) -> str:
    # Deepgram accepts UTF-8, but you can customize if needed
    return text.replace('*', '')

class DeepgramStreamProcessor:
    def __init__(self, client: object) -> None:
        self._client = client

    async def _preprocess_stream(self, text_stream: AsyncIterable[str]) -> AsyncIterable[str]:
        """Clean text by removing incompatible characters and custom markers."""
        async for chunk in text_stream:
            cleaned = remove_incompatible_characters(chunk)
            yield cleaned

    def _find_sentence(self, buffer_text: str) -> tuple[str, str]:
        """
        Extract the first complete sentence from the buffer using a language-agnostic
        approach for decimal points.
        """
        if not buffer_text:
            return "", ""

        DECIMAL_PLACEHOLDER = "##DEC##"
        safe_text = re.sub(r'(\d)\.(\d)', fr'\1{DECIMAL_PLACEHOLDER}\2', buffer_text)

        # Only split if the dot is not part of a list number (e.g., "1.", "2.", etc.)
        match = re.search(r"(?<!\d)[.!?]", safe_text)
        if match:
            end_index = match.start() + 1
            sentence_part = safe_text[:end_index]
            rest_part = safe_text[end_index:]
            final_sentence = sentence_part.replace(DECIMAL_PLACEHOLDER, '.')
            final_rest = rest_part.replace(DECIMAL_PLACEHOLDER, '.')
            return final_sentence.strip(), final_rest.strip()

        max_chars = 200
        if len(safe_text) > max_chars:
            search_area = safe_text[:max_chars + 20]
            last_space_index = search_area.rfind(" ")
            if last_space_index > 0:
                sentence_part = safe_text[:last_space_index]
                rest_part = safe_text[last_space_index:]
            else:
                sentence_part = safe_text[:max_chars]
                rest_part = safe_text[max_chars:]
            final_sentence = sentence_part.replace(DECIMAL_PLACEHOLDER, '.')
            final_rest = rest_part.replace(DECIMAL_PLACEHOLDER, '.')
            return final_sentence.strip(), final_rest.strip()

        return "", buffer_text

    async def _sentence_generator(self, text_stream: AsyncIterable[str]) -> AsyncGenerator[str, None]:
        """Yield complete, speakable sentences from a text stream."""
        buffer = ""
        generated_sentences = 0
        async for chunk in text_stream:
            buffer += chunk
            while True:
                sentence, rest = self._find_sentence(buffer)
                if sentence:
                    if re.search(r'\w', sentence):
                        generated_sentences += 1
                        yield sentence
                    buffer = rest
                else:
                    break
        if buffer.strip() and re.search(r'\w', buffer.strip()):
            generated_sentences += 1
            yield buffer.strip()
        if generated_sentences == 0:
            _LOGGER.warning("No sentence was generated for synthesis from the received text.")

    def _trim_end_of_audio(self, audio_data: bytes) -> bytes:
        """
        Use pydub to trim TRIM_MS_FROM_END ms from the end of each mp3 fragment.
        Replicates the logic from the edge-tts example.
        """
        if not AudioSegment:
            return audio_data
        try:
            segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
            if len(segment) > TRIM_MS_FROM_END:
                trimmed = segment[:-TRIM_MS_FROM_END]
                out_buffer = io.BytesIO()
                trimmed.export(out_buffer, format="mp3")
                return out_buffer.getvalue()
            else:
                out_buffer = io.BytesIO()
                segment.export(out_buffer, format="mp3")
                return out_buffer.getvalue()
        except Exception as e:
            _LOGGER.warning("Could not trim end of audio, returning original. Error: %s", e)
            return audio_data

    def _strip_id3(self, mp3_bytes: bytes) -> bytes:
        """Remove ID3v2 headers from an mp3 fragment (except the first one)."""
        if mp3_bytes[:3] == b"ID3":
            # ID3v2 header is 10 bytes + size
            size = int.from_bytes(mp3_bytes[6:10], "big")
            return mp3_bytes[10+size:]
        return mp3_bytes

    async def async_process_stream(
        self, text_stream: AsyncIterable[str], model: str
    ) -> AsyncIterable[bytes]:
        """
        Process the text into sentences, synthesize each one, trim the end and buffer them.
        Each fragment is yielded as a valid mp3 for streaming.
        """
        if not AudioSegment:
            raise RuntimeError("pydub is not available to join mp3 fragments")

        output_queue = asyncio.Queue(maxsize=10)
        processing_task = asyncio.create_task(
            self._process_all_text(text_stream, output_queue, model)
        )

        idx = 0
        while True:
            try:
                chunk = await output_queue.get()
                if chunk is None:
                    break
                try:
                    segment = AudioSegment.from_file(io.BytesIO(chunk), format="mp3")
                    out_buffer = io.BytesIO()
                    await asyncio.to_thread(segment.export, out_buffer, format="mp3")
                    mp3_bytes = out_buffer.getvalue()
                    yield mp3_bytes
                except Exception as e:
                    _LOGGER.error("Error decoding mp3 chunk #%d: %s", idx, e)
                output_queue.task_done()
                idx += 1
            except asyncio.CancelledError:
                break

        if not processing_task.done():
            processing_task.cancel()
            await asyncio.sleep(0)

    async def _process_all_text(
        self, text_stream: AsyncIterable[str], output_queue: asyncio.Queue, model: str
    ):
        try:
            sentences_generator = self._sentence_generator(self._preprocess_stream(text_stream))
            async for sentence in sentences_generator:
                await asyncio.sleep(SYNTHESIS_DELAY_S)
                try:
                    audio_bytes = await self._client.async_synthesize_speech(
                        text=sentence,
                        model=model,
                        encoding="mp3",
                    )
                    if not audio_bytes:
                        _LOGGER.error("Deepgram returned empty audio for sentence: '%s'", sentence)
                        continue
                    trimmed_mp3 = await asyncio.to_thread(self._trim_end_of_audio, audio_bytes)
                    if trimmed_mp3:
                        await output_queue.put(trimmed_mp3)
                except Exception as e:
                    _LOGGER.error("Error processing sentence '%s': %s", sentence[:30], e, exc_info=True)
        finally:
            await output_queue.put(None)
