"""공통 정규표현식 패턴 정의"""
import re

# 기본 구성 요소 패턴
SUBJECT_CODE_PATTERN = r"[a-zA-Z0-9]+"  # 과목코드: 영숫자
CLASS_NUM_PATTERN = r"\d+"              # 분반: 숫자
STUDENT_ID_PATTERN = r"\d+"             # 학번: 숫자

# 과제 디렉토리 패턴: 숨김 디렉토리가 아닌 모든 디렉토리명 허용 (동적 과제명 지원)
HOMEWORK_DIR_PATTERN = r"[^./][^/]*"

# 조합된 패턴들
CLASS_DIV_PATTERN = f"({SUBJECT_CODE_PATTERN})-({CLASS_NUM_PATTERN})"  # 과목-분반

# 컴파일된 정규표현식 객체들
HOSTNAME_REGEX = re.compile(f"jcode-{CLASS_DIV_PATTERN}-({STUDENT_ID_PATTERN})")

WORKSPACE_PATH_REGEX = re.compile(
    f"^(?:/workspace/{CLASS_DIV_PATTERN}-{STUDENT_ID_PATTERN}/({HOMEWORK_DIR_PATTERN})|"
    f"/home/coder/project/({HOMEWORK_DIR_PATTERN}))"
)
