from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import UUID, uuid4


@dataclass(frozen=True)
class SourceFileInfo:
    """소스 코드 경로 정보를 관리하는 클래스"""

    class_div: str  # 과목-분반 (예: os-1)
    hw_name: str  # 표시·감사용 과제 디렉터리
    assignment_id: int
    student_id: str  # 학번 (예: 202012180)
    filename: str  # 파일명 (예: src@app@test.py)
    target_file_path: Path  # 대상 파일 절대 경로
    timestamp: str  # 이벤트 타임스탬프 (YYYYMMDD_HHMMSS)
    event_id: UUID
    occurred_at: datetime

    @classmethod
    def from_parsed_data(
        cls, parsed_data: Dict[str, Any], target_file_path: Path
    ) -> "SourceFileInfo":
        """파싱된 데이터로부터 SourceFileInfo 생성"""
        occurred_at = datetime.now(timezone.utc)
        return cls(
            class_div=parsed_data["class_div"],
            hw_name=parsed_data["hw_name"],
            assignment_id=parsed_data["assignment_id"],
            student_id=parsed_data["student_id"],
            filename=parsed_data["filename"],
            target_file_path=target_file_path,
            timestamp=occurred_at.strftime("%Y%m%d_%H%M%S"),
            event_id=uuid4(),
            occurred_at=occurred_at,
        )
