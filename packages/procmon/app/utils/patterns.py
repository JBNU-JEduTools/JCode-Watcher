"""공통 정규표현식 패턴 정의"""
import re

# 기본 구성 요소 패턴
SUBJECT_CODE_PATTERN = r"[a-zA-Z0-9]+"  # 과목코드: 영숫자
CLASS_NUM_PATTERN = r"\d+"              # 분반: 숫자
STUDENT_ID_PATTERN = r"\d+"             # 학번: 숫자
HOMEWORK_DIR_PATTERN = r"hw(?:20|1[0-9]|[0-9])"  # 과제 디렉터리: hw0-hw20

# 조합된 패턴들
CLASS_DIV_PATTERN = f"({SUBJECT_CODE_PATTERN})-({CLASS_NUM_PATTERN})"  # 과목-분반

# 컴파일된 정규표현식 객체들
HOSTNAME_REGEX = re.compile(f"jcode-{CLASS_DIV_PATTERN}-({STUDENT_ID_PATTERN})")

WORKSPACE_PATH_REGEX = re.compile(
    f"^(?:/workspace/{CLASS_DIV_PATTERN}-{STUDENT_ID_PATTERN}/({HOMEWORK_DIR_PATTERN})|"
    f"/home/coder/project/({HOMEWORK_DIR_PATTERN}))"
)