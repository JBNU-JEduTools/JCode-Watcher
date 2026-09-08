import json
import re
import ssl
import time
from pathlib import Path

import aiohttp
from app.config.settings import settings


class CourseIdResolver:
    def __init__(self):
        self._cache: dict[str, tuple[float, int]] = {}
        self._static = json.loads(settings.COURSE_ID_MAP_JSON or "{}")
        if not isinstance(self._static, dict):
            raise ValueError("COURSE_ID_MAP_JSON은 객체여야 합니다.")

    async def resolve(self, class_div: str) -> int:
        if not re.fullmatch(r"[A-Za-z0-9]+-\d+", class_div):
            raise ValueError(f"유효하지 않은 class_div입니다: {class_div}")
        static = self._static.get(class_div)
        if static is not None:
            return self._positive_id(static)
        cached = self._cache.get(class_div)
        if cached and cached[0] > time.monotonic():
            return cached[1]

        prefix = "jcode-dev-" if settings.JCODE_ENVIRONMENT == "dev" else "jcode-"
        namespace = f"{prefix}{class_div.lower()}"
        api_url = settings.KUBERNETES_API_URL.rstrip("/")
        if not api_url:
            api_url = (
                f"https://{settings.KUBERNETES_SERVICE_HOST}:"
                f"{settings.KUBERNETES_SERVICE_PORT_HTTPS}"
            )
        token = Path(settings.KUBERNETES_TOKEN_PATH).read_text().strip()
        ssl_context = None
        if api_url.startswith("https://"):
            ssl_context = ssl.create_default_context(cafile=settings.KUBERNETES_CA_PATH)
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {token}"}
        ) as session:
            async with session.get(
                f"{api_url}/api/v1/namespaces/{namespace}",
                ssl=ssl_context,
                timeout=settings.API_TIMEOUT_TOTAL,
            ) as response:
                response.raise_for_status()
                body = await response.json()
        course_id = self._positive_id(
            body.get("metadata", {}).get("annotations", {}).get("jcode.io/course-id")
        )
        self._cache[class_div] = (
            time.monotonic() + settings.COURSE_ID_CACHE_SECONDS,
            course_id,
        )
        return course_id

    @staticmethod
    def _positive_id(value) -> int:
        course_id = int(value)
        if course_id <= 0:
            raise ValueError("course_id는 양수여야 합니다.")
        return course_id
