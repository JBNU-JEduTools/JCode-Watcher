import re
import os
from typing import Optional
from pathlib import Path
from ..utils.logging import get_logger

class HomeworkChecker:
    """과제 경로 검증기"""
    def __init__(self):
        self.logger = get_logger(__name__)
        # hw 디렉토리 이름이 정확히 매칭되도록 경계 조건 추가
        homework_pattern = r'hw(?:20|1[0-9]|[1-9])(?=/|$)'  # hw1-hw20 (순서 중요, 끝 경계 추가)
        self.pattern = re.compile(
            r'^(?:/workspace/[a-z]+-\d+-\d+/({homework_pattern})|'  # /workspace/subject-section-id/hw{n}
            r'/home/coder/project/({homework_pattern}))'   # /home/coder/project/hw{n}
            .format(homework_pattern=homework_pattern)
        )
        self.logger.info("[HomeworkChecker] 초기화 완료")

    def get_homework_info(self, path: str) -> str | None:
        """과제 경로에서 과제 디렉토리명 추출

        Args:
            path: 완전한 절대 경로 (소스 파일 또는 바이너리 파일 경로)
                 예: /os-1-202012345/hw1/main.c 또는 /home/coder/project/hw1/main

        Returns:
            str | None: 경로가 과제 형식에 맞는 경우 hw 디렉토리명(예: hw1),
                       형식에 맞지 않는 경우 None
        """
        try:
            return self._validate(path)
        except Exception as e:
            self.logger.error(f"[HomeworkChecker] 경로 검사 실패: {str(e)}")
            return None

    def _validate(self, path: str | Path) -> str | None:
        """경로 검증 및 hw 디렉토리명 추출"""
        try:
            if path is None:
                self.logger.debug("[HomeworkChecker] 검증 실패 - 경로가 None입니다")
                return None

            # 이스케이프 문자 거부
            if any(c in str(path) for c in ['\n', '\t', '\r']):
                self.logger.debug(f"[HomeworkChecker] 검증 실패 - 경로에 이스케이프 문자가 포함되어 있습니다: {path}")
                return None

            # 경로 정규화
            try:
                normalized_path = os.path.normpath(str(path))
            except Exception as e:
                self.logger.debug(f"[HomeworkChecker] 검증 실패 - 경로 정규화 실패: {path}, 오류: {e}")
                return None

            # 상대 경로 거부
            if not normalized_path.startswith('/'):
                self.logger.debug(f"[HomeworkChecker] 검증 실패 - 상대 경로는 지원하지 않습니다: {normalized_path}")
                return None

            # 중첩된 hw 디렉토리 체크
            parts = normalized_path.split('/')
            hw_count = sum(1 for part in parts if part.startswith('hw'))
            if hw_count > 1:
                self.logger.debug(f"[HomeworkChecker] 검증 실패 - 중첩된 hw 디렉토리가 있습니다: {normalized_path}")
                return None

            # 정규화된 경로로 패턴 매칭
            match = self.pattern.match(normalized_path)
            if not match:
                self.logger.debug(f"[HomeworkChecker] 검증 실패 - 경로 패턴이 일치하지 않습니다: {normalized_path}")
                return None

            # hw 디렉토리명 반환 (두 패턴 중 매칭된 그룹)
            hw_dir = match.group(1) or match.group(2)
            self.logger.debug(f"[HomeworkChecker] 검증 성공 - 경로: {normalized_path}, hw: {hw_dir}")
            return hw_dir

        except (TypeError, AttributeError, ValueError) as e:
            self.logger.debug(f"[HomeworkChecker] 검증 실패 - 파싱 중 오류 발생: {path}, 오류: {e}")
            return None 