# inotifywait -m -r -e modify  --format '%w%f %e' --exclude '.*\.swp' "/home/ubuntu/jcode/os-3-202012180/config/workspace" > bench.log



import os
import time
import threading

# 설정값
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(CURRENT_DIR, 'bench')  # 현재 경로 아래 bench 폴더 생성
FILE_COUNT = 500       # 동시에 생성·수정할 파일 개수
MODIFY_COUNT = 5    # 각 파일이 수정될 횟수
DELAY_BETWEEN_MODS = 0.1  # 각 수정 사이 지연(초)

# 스레드 함수: 단일 파일을 여러 번 수정
def modify_file(file_index):
    file_path = os.path.join(TEST_DIR, f'stress_test_{file_index}.c')

    # 초기에 파일을 생성
    with open(file_path, 'w') as f:
        f.write(f"Initial content for file {file_index}\n")

    # 여러 번 수정
    for i in range(MODIFY_COUNT):
        with open(file_path, 'a') as f:
            f.write(f"Modification round {i}\n")
        time.sleep(DELAY_BETWEEN_MODS)

# 메인 함수
if __name__ == '__main__':
    # 벤치마크 시작 시간
    start_time = time.time()

    # 테스트 디렉토리 생성
    if not os.path.exists(TEST_DIR):
        os.makedirs(TEST_DIR)

    # 기존 파일 제거(재실행 시 깨끗한 환경으로 시작하도록)
    for filename in os.listdir(TEST_DIR):
        if filename.startswith('stress_test_'):
            os.remove(os.path.join(TEST_DIR, filename))

    # 스레드 목록
    threads = []

    # 여러 파일에 대해 수정 스레드 시작
    for idx in range(FILE_COUNT):
        t = threading.Thread(target=modify_file, args=(idx,))
        t.start()
        threads.append(t)

    # 모든 스레드가 작업을 마칠 때까지 대기
    for t in threads:
        t.join()

    # 벤치마크 종료
    end_time = time.time()
    
    # 결과 출력
    print("================ Stress Test Complete ================")
    print(f"총 파일 개수: {FILE_COUNT}")
    print(f"각 파일당 수정 횟수: {MODIFY_COUNT}")
    print(f"최종 총 수정 이벤트 수: {FILE_COUNT * MODIFY_COUNT}")
    print(f"실행 시간: {end_time - start_time:.2f}초")
