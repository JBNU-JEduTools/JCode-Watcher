import re
from .logger import logger
from typing import Optional
from .models.student_info import StudentInfo
from .models.process import Process


class StudentParser:
    """hostname에서 학생 정보를 파싱하는 파서"""

    # 패턴: jcode-{과목}-{분반}-{학번}
    HOSTNAME_PATTERN = re.compile(r'jcode-([a-z]+)-(\d+)-(\d+)')

    def __init__(self):
        self.logger = logger

    def parse_from_process(self, process: Process) -> Optional[StudentInfo]:
        """Process 객체의 hostname에서 학생 정보 추출

        Args:
            process: BPF에서 수집된 Process 객체
        """
        if not process or not process.hostname:
            self.logger.debug("Process 또는 hostname이 없음")
            return None

        match = self.HOSTNAME_PATTERN.match(process.hostname)
        if not match:
            self.logger.debug(f"hostname 패턴 불일치: {process.hostname}")
            return None

        try:
            subject, class_num, student_id = match.groups()
            class_div = f"{subject}-{class_num}"

            return StudentInfo(
                student_id=student_id,
                class_div=class_div
            )
        except ValueError as e:
            self.logger.error(f"StudentInfo 생성 실패: {e}")
            return None