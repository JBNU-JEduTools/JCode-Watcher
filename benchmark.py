import time
import random
import sys

FILE_PATH = "dummy_code.py"  # 수정을 가할 대상 파일
INTERVAL = 1                 # 수정 간격(초)
MAX_ITER = 50                # 최대 수정 횟수 (필요에 따라 조정)

# 수정할 때 추가할 임시 줄(주석 등)
ADDITIONAL_LINES = [
    "# TODO: This is a dummy comment.\n",
    "# Random comment generated.\n",
    "# Another random line.\n",
    "# Inserting line for inotify test.\n"
]

def modify_code():
    """
    1) 기존 코드를 불러옴
    2) 랜덤하게 몇 줄을 추가하거나 삭제
    3) 덮어쓰기(저장)
    4) 수정 시각 출력
    """
    try:
        # 1) 기존 파일 읽기
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"파일 {FILE_PATH}이(가) 존재하지 않습니다.")
        sys.exit(1)

    # 2) 무작위로 한두 줄 수정(추가 or 삭제)
    action = random.choice(["add", "delete"])
    
    if action == "add":
        # 랜덤 위치에 새 라인을 삽입
        new_line = random.choice(ADDITIONAL_LINES)
        insert_idx = random.randint(0, len(lines))
        lines.insert(insert_idx, new_line)
        print(f"[{time.strftime('%H:%M:%S')}] Added a line at {insert_idx}")
    else:
        # 삭제 가능한 경우에만 삭제
        if len(lines) > 0:
            delete_idx = random.randint(0, len(lines) - 1)
            removed = lines.pop(delete_idx)
            print(f"[{time.strftime('%H:%M:%S')}] Deleted line {delete_idx}: {removed.strip()}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] No lines to delete; skip delete.")

    # 3) 변경 내용을 다시 파일에 저장
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def main():
    print(f"=== Auto Modifier Start ===")
    print(f"타겟 파일: {FILE_PATH}")
    print(f"수정 간격: {INTERVAL}초, 최대 반복: {MAX_ITER}회\n")
    
    for i in range(MAX_ITER):
        modify_code()
        # 4) 타임스탬프 로그 출력
        print(f" => {i+1}번째 수정 완료 (총 {MAX_ITER}회 중)")
        
        # 5) 1초 대기
        time.sleep(INTERVAL)

    print("\n=== 모든 수정 작업이 완료되었습니다. ===")

if __name__ == "__main__":
    main()
