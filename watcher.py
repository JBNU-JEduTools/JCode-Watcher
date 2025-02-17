import os
import time
import glob
import shutil
import sys
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Config:
    """설정 관련 상수 정의"""
    BASE_PATH = '/watcher/codes'
    SNAPSHOT_PATH = '/watcher/snapshots'
    WATCH_PATTERN = "*/config/workspace"
    HOMEWORK_PATTERN = "hw*"
    SUPPORTED_EXTENSIONS = ('.c', '.cpp', '.py', '.java', '.js')

class PathManager:
    """경로 관리 및 처리를 담당하는 클래스"""
    @staticmethod
    def get_watch_directories():
        """감시할 과제 디렉토리 목록을 반환"""
        watch_dirs = []
        base_dirs = glob.glob(os.path.join(Config.BASE_PATH, Config.WATCH_PATTERN))
        
        for workspace in base_dirs:
            hw_dirs = glob.glob(os.path.join(workspace, Config.HOMEWORK_PATTERN))
            watch_dirs.extend(hw_dirs)
        
        return watch_dirs

    @staticmethod
    def parse_user_info(user_dir):
        """사용자 디렉토리에서 class-div와 student_id 추출
        
        Args:
            user_dir (str): 예) 'os-3-202012180'
            
        Returns:
            tuple: (class_div, student_id) 예) ('os-3', '202012180')
        """
        last_hyphen_index = user_dir.rindex('-')
        class_div = user_dir[:last_hyphen_index]
        student_id = user_dir[last_hyphen_index + 1:]
        return class_div, student_id

    @staticmethod
    def create_snapshot_path(file_path):
        """스냅샷 저장 경로 생성
        
        Args:
            file_path (str): 원본 파일 경로
            
        Returns:
            tuple: (snapshot_dir, snapshot_filename)
            
        Path format:
            루트 파일: /snapshots/:class_div/:hw_name/:student_id/:filename/{timestamp}.ext
            서브디렉토리 파일: /snapshots/:class_div/:hw_name/:student_id/:folder1@folder2@...@filename/{timestamp}.ext
            
            예1: /snapshots/os-3/hw1/202012180/test.c/20250217_095542.c  (루트 파일)
            예2: /snapshots/os-3/hw1/202012180/folder1@folder2@test.c/20250217_095542.c  (서브디렉토리 파일)
        """
        rel_path = os.path.relpath(file_path, Config.BASE_PATH)
        path_parts = rel_path.split(os.sep)
        
        # 사용자 정보 추출
        user_dir = path_parts[0]
        class_div, student_id = PathManager.parse_user_info(user_dir)
        
        # 과제 이름과 상대 경로 추출
        workspace_index = path_parts.index('workspace')
        hw_name = path_parts[workspace_index + 1]
        
        # 파일 정보
        filename = os.path.basename(file_path)
        base_name, ext = os.path.splitext(filename)
        
        # 타임스탬프 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 스냅샷 디렉토리 경로 생성
        is_in_subdirectory = len(path_parts) > workspace_index + 3
        if is_in_subdirectory:
            # hw1 이후부터 파일명 이전까지의 모든 폴더를 @로 연결
            folders = path_parts[workspace_index + 2:-1]
            snapshot_subpath = '@'.join(folders + [filename])
        else:
            snapshot_subpath = filename
            
        snapshot_dir = os.path.join(
            Config.SNAPSHOT_PATH,
            class_div,        # 예: os-3
            hw_name,          # 예: hw1
            student_id,       # 예: 202012180
            snapshot_subpath  # 예: folder1@folder2@test.c 또는 test.c
        )
        
        # 스냅샷 파일명: timestamp.ext
        snapshot_filename = f"{timestamp}{ext}"
        
        return snapshot_dir, snapshot_filename

class CodeChangeHandler(FileSystemEventHandler):
    """파일 변경 감지 및 스냅샷 생성 핸들러"""
    def __init__(self):
        self.last_snapshot = {}
        self.debounce_time = 1.0

    def on_modified(self, event):
        if event.is_directory:
            return
        
        if event.src_path.endswith(Config.SUPPORTED_EXTENSIONS):
            current_time = time.time()
            last_time = self.last_snapshot.get(event.src_path, 0)
            
            if current_time - last_time > self.debounce_time:
                self._take_snapshot(event.src_path)
                self.last_snapshot[event.src_path] = current_time
    
    def on_created(self, event):
        if event.is_directory:
            return
            
        if event.src_path.endswith(Config.SUPPORTED_EXTENSIONS):
            current_time = time.time()
            self._take_snapshot(event.src_path)
            self.last_snapshot[event.src_path] = current_time

    def _take_snapshot(self, file_path):
        """파일 스냅샷 생성"""
        try:
            snapshot_dir, snapshot_filename = PathManager.create_snapshot_path(file_path)
            os.makedirs(snapshot_dir, exist_ok=True)
            
            snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
            shutil.copy2(file_path, snapshot_path)
            
            # 상대 경로로 로그 출력
            rel_snapshot_path = os.path.relpath(snapshot_path, Config.SNAPSHOT_PATH)
            print(f"스냅샷 생성됨: {rel_snapshot_path}")
            
        except Exception as e:
            print(f"스냅샷 생성 중 오류 발생 - 파일: {file_path}, 오류: {e}")

def initialize_directories():
    """필요한 디렉토리 초기화 및 검증"""
    watch_dirs = PathManager.get_watch_directories()
    
    if not watch_dirs:
        print(f"오류: 감시할 디렉토리가 존재하지 않습니다.")
        print(f"'{Config.BASE_PATH}/[사용자]/config/workspace/hw*' 경로가 하나 이상 존재해야 합니다.")
        sys.exit(1)
    
    os.makedirs(Config.SNAPSHOT_PATH, exist_ok=True)
    return watch_dirs

def start_watching():
    """파일 감시 시작"""
    watch_dirs = initialize_directories()
    event_handler = CodeChangeHandler()
    observer = Observer()
    
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

if __name__ == "__main__":
    start_watching()