from dataclasses import dataclass


@dataclass
class StudentInfo:
    """학생 정보"""

    student_id: str
    class_div: str  # 예: "os-1"

    def __post_init__(self):
        if not self.student_id or not self.class_div:
            raise ValueError("student_id와 class_div는 필수입니다")
