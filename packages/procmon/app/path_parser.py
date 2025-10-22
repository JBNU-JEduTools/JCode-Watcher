import re
import os
from app.utils.logger import get_logger
from typing import Optional
from pathlib import Path
from app.utils.patterns import WORKSPACE_PATH_REGEX


class PathParser:
    """경로에서 hw 디렉토리명을 파싱하는 도구

    - 정상적인 hw 경로면 "hw1", "hw2" 등의 문자열 반환
    - 과제 디렉토리가 아니면 None 반환
    - 비정상 입력은 예외 발생
    """

    def __init__(self):
        self.logger = get_logger("path_parser")

    def parse(self, path: str | Path) -> Optional[str]:
        """경로에서 hw 디렉토리명을 추출
        Args:
            path: 절대 경로 (예: /workspace/os-1-202012345/hw1/main.c)
        Returns:
            hw 디렉토리명 (예: "hw1") 또는 None
        """
        if path is None:
            raise ValueError("경로가 None입니다")

        path_str = str(path)

        # 이스케이프 문자 금지
        if any(c in path_str for c in ["\n", "\t", "\r"]):
            raise ValueError(f"경로에 이스케이프 문자 포함: {path_str}")

        # 정규화된 절대 경로만 허용
        normalized = os.path.normpath(path_str)
        if not normalized.startswith("/"):
            raise ValueError(f"상대 경로 지원 안함: {normalized}")

        # 중첩된 hw 디렉토리 거부
        parts = normalized.split("/")
        if sum(1 for p in parts if p.startswith("hw")) > 1:
            raise ValueError(f"중첩된 hw 디렉토리 감지: {normalized}")

        # 패턴 매칭
        match = WORKSPACE_PATH_REGEX.match(normalized)
        if not match:
            return None

        hw_dir = match.group(3) or match.group(4)
        self.logger.debug("PathParser 파싱 성공", path=normalized, homework_dir=hw_dir)
        return hw_dir
