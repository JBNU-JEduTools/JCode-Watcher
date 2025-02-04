import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil
from datetime import datetime
import sys
import glob

# 기본 디렉토리 설정
BASE_PATH = "/home/ubuntu/jcode"  # 기본 경로 + {username}/config/workspace 
BASE_SNAPSHOT_DIRECTORY = "snapshots"  # 스냅샷 저장 기본 경로

# 감시할 디렉토리와 스냅샷 저장 디렉토리 확인 및 생성
def check_directories():
    # 모든 사용자의 config 디렉토리 찾기
    watch_dirs = glob.glob(os.path.join(BASE_PATH, "*/config/workspace"))
    
    if not watch_dirs:
        print(f"오류: 감시할 디렉토리가 존재하지 않습니다.")
        print(f"'{BASE_PATH}/[사용자]/config/workspace' 경로가 하나 이상 존재해야 합니다.")
        sys.exit(1)
    
    if not os.path.exists(BASE_SNAPSHOT_DIRECTORY):
        print(f"스냅샷 저장 경로 '{BASE_SNAPSHOT_DIRECTORY}'가 존재하지 않습니다. 자동으로 생성합니다.")
        os.makedirs(BASE_SNAPSHOT_DIRECTORY, exist_ok=True)
    
    return watch_dirs

def start_watching():
    watch_dirs = check_directories()  # 감시할 디렉토리 목록 가져오기
    event_handler = CodeChangeHandler()
    observer = Observer()
    
    # 각 사용자의 workspace 디렉토리에 대해 감시 설정
    for watch_dir in watch_dirs:
        observer.schedule(event_handler, watch_dir, recursive=True)
        print(f"디렉토리 감시 추가: {watch_dir}")
    
    observer.start()
    
    try:
        print("모든 workspace 디렉토리 감시 시작...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n감시 종료")
    
    observer.join()

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_snapshot = {}
        self.debounce_time = 1.0

    def on_modified(self, event):
        if event.is_directory:
            return
        
        if event.src_path.endswith(('.c', '.cpp', '.py', '.java', '.js')):
            current_time = time.time()
            last_time = self.last_snapshot.get(event.src_path, 0)
            
            if current_time - last_time > self.debounce_time:
                self._take_snapshot(event.src_path)
                self.last_snapshot[event.src_path] = current_time
    
    def on_created(self, event):
        if event.is_directory:
            return
            
        if event.src_path.endswith(('.c', '.cpp', '.py', '.java', '.js')):
            current_time = time.time()
            self._take_snapshot(event.src_path)
            self.last_snapshot[event.src_path] = current_time

    def _take_snapshot(self, file_path):
        # 경로에서 사용자 디렉토리 추출
        path_parts = file_path.split(os.sep)
        user_index = path_parts.index('jcode') + 1
        user_dir = path_parts[user_index]
        
        # 파일 정보 추출
        filename = os.path.basename(file_path)
        base_name, ext = os.path.splitext(filename)
        
        # 스냅샷 저장 구조:
        # snapshots/user2/hello.c/hello_20250122_202743.c
        snapshot_dir = os.path.join(BASE_SNAPSHOT_DIRECTORY, user_dir, filename)
        os.makedirs(snapshot_dir, exist_ok=True)
        
        # 타임스탬프와 스냅샷 파일명 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_filename = f"{base_name}_{timestamp}{ext}"
        snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
        
        try:
            shutil.copy2(file_path, snapshot_path)
            print(f"스냅샷 생성됨: {user_dir}/{filename}/{snapshot_filename}")
        except Exception as e:
            print(f"스냅샷 생성 중 오류 발생: {e}")

if __name__ == "__main__":
    start_watching()