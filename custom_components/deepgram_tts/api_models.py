from __future__ import annotations

import aiohttp
import async_timeout

class DeepgramModelsClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._models_url = "https://api.deepgram.com/v1/models"

    async def fetch_models(self) -> dict:
        async with async_timeout.timeout(10):
            response = await self._session.get(self._models_url)
            response.raise_for_status()
            return await response.json()
