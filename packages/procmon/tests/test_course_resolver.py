from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_static_course_mapping_is_used_without_kubernetes():
    with patch("app.course_resolver.settings") as settings:
        settings.COURSE_ID_MAP_JSON = '{"os-1": 7}'
        from app.course_resolver import CourseIdResolver

        assert await CourseIdResolver().resolve("os-1") == 7


@pytest.mark.asyncio
async def test_invalid_course_key_is_rejected():
    with patch("app.course_resolver.settings") as settings:
        settings.COURSE_ID_MAP_JSON = "{}"
        from app.course_resolver import CourseIdResolver

        with pytest.raises(ValueError, match="class_div"):
            await CourseIdResolver().resolve("../watcher")
