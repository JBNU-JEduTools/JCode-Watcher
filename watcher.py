import os
import time
import glob
import shutil
import sys
import queue
import threading
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import hashlib

class Config:
    """설정 관련 상수 정의"""
    BASE_PATH = '/watcher/codes'
    SNAPSHOT_PATH = '/watcher/snapshots'
    # BASE_PATH = '/home/ubuntu/jcode'
    # SNAPSHOT_PATH = '/home/ubuntu/watcher/watcher.code/snapshots'
    WATCH_PATTERN = "*/config/workspace"
    HOMEWORK_PATTERN = "hw*"
    QUEUE_SIZE = 65536

    # 감시할 파일 확장자
    SUPPORTED_EXTENSIONS = (
        # 소스 코드
        '.c', '.cpp', '.h', '.hpp',
        '.py', '.java'
    )

    # 무시할 파일/디렉토리 패턴
    IGNORE_PATTERNS = {
        # 시스템 파일
        '.DS_Store',
        'Thumbs.db',
        '.git',
        '__pycache__',
        '*.pyc',
        # 빌드 디렉토리
        'build/',
        'dist/',
        'target/',
        'node_modules/',
        # 로그 파일
        '*.log',
        # 바이너리/오브젝트 파일
        '*.o',
        '*.so',
        '*.dylib',
        '*.dll',
        '*.exe',
        '*.out',
        # IDE 설정
        '.idea/',
        '.vscode/',
        '.vs/',
        # 기타
        '*.tmp',
        '*.temp',
        '*.swp',
        '~*'
    }

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

class FileHashManager:
    """파일 해시 관리 클래스"""
    def __init__(self):
        self.file_hashes = {}  # {file_path: last_hash}
    
    def is_file_changed(self, file_path):
        """파일 내용이 변경되었는지 확인
        
        Args:
            file_path (str): 확인할 파일 경로
            
        Returns:
            bool: 파일 내용이 변경되었으면 True
        """
        try:
            current_hash = self._calculate_file_hash(file_path)
            last_hash = self.file_hashes.get(file_path)
            
            if last_hash != current_hash:
                self.file_hashes[file_path] = current_hash
                return True
            return False
        except Exception as e:
            print(f"파일 해시 계산 중 오류 발생: {e}")
            return True  # 오류 발생 시 안전하게 True 반환
    
    def _calculate_file_hash(self, file_path):
        """파일의 MD5 해시값 계산"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

class FileFilter:
    """파일 필터링을 담당하는 클래스"""
    def __init__(self):
        self.ignore_patterns = self._compile_patterns(Config.IGNORE_PATTERNS)

    def _compile_patterns(self, patterns):
        """와일드카드 패턴을 정규식으로 변환"""
        import fnmatch
        import re
        return [re.compile(fnmatch.translate(p)) for p in patterns]

    def should_ignore(self, file_path):
        """파일이 무시되어야 하는지 확인
        
        Args:
            file_path (str): 검사할 파일 경로
            
        Returns:
            bool: 무시해야 하면 True
        """
        # 상대 경로로 변환
        rel_path = os.path.relpath(file_path, Config.BASE_PATH)
        
        # 확장자 검사
        if not file_path.endswith(Config.SUPPORTED_EXTENSIONS):
            return True

        # 무시 패턴 검사
        for pattern in self.ignore_patterns:
            if pattern.match(rel_path) or any(pattern.match(part) 
                for part in rel_path.split(os.sep)):
                return True

        return False

class SnapshotWorker:
    """스냅샷 생성을 담당하는 워커 클래스"""
    def __init__(self, snapshot_queue, num_workers=4):  # 기본값 4개 워커
        self.queue = snapshot_queue
        self.running = False
        self.worker_threads = []
        self.num_workers = num_workers
        self.success_count = 0
        self.count_lock = threading.Lock()  # 카운터 동기화를 위한 락

    def start(self):
        """워커 쓰레드들 시작"""
        self.running = True
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._process_queue,
                name=f"SnapshotWorker-{i+1}"
            )
            worker.daemon = True
            worker.start()
            self.worker_threads.append(worker)
        print(f"스냅샷 워커 {self.num_workers}개 시작됨")

    def stop(self):
        """워커 쓰레드들 종료"""
        self.running = False
        for worker in self.worker_threads:
            worker.join()
        print(f"스냅샷 워커 종료됨 (성공한 스냅샷: {self.success_count}개)")

    def _process_queue(self):
        """큐에서 파일 경로를 가져와 스냅샷 생성"""
        while self.running:
            try:
                file_path = self.queue.get(timeout=1.0)
                self._create_snapshot(file_path)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"스냅샷 처리 중 오류 발생: {e}")

    def _create_snapshot(self, file_path):
        """파일 스냅샷 생성"""
        try:
            snapshot_dir, snapshot_filename = PathManager.create_snapshot_path(file_path)
            os.makedirs(snapshot_dir, exist_ok=True)
            
            snapshot_path = os.path.join(snapshot_dir, snapshot_filename)
            shutil.copy2(file_path, snapshot_path)
            
            # 쓰레드 안전하게 카운트 증가
            with self.count_lock:
                self.success_count += 1
                current_count = self.success_count
            
            # 상대 경로로 로그 출력
            rel_snapshot_path = os.path.relpath(snapshot_path, Config.SNAPSHOT_PATH)
            print(f"스냅샷 생성됨 ({current_count}번째 성공): {rel_snapshot_path}")
            
        except Exception as e:
            print(f"스냅샷 생성 중 오류 발생 - 파일: {file_path}, 오류: {e}")

class CodeChangeHandler(FileSystemEventHandler):
    """파일 변경 감지 핸들러"""
    def __init__(self, snapshot_queue):
        self.queue = snapshot_queue
        self.hash_manager = FileHashManager()
        self.file_filter = FileFilter()
        self.event_count = 0  # 이벤트 카운트 추가

    def _handle_file_event(self, event_path, event_type):
        """파일 이벤트 공통 처리 로직"""
        try:
            # 무시해야 할 파일 검사
            # if self.file_filter.should_ignore(event_path):
            #     return

            # 파일 내용 변경 확인
            # if not self.hash_manager.is_file_changed(event_path):
            #     return  # 내용이 변경되지 않았으면 무시
            
            self.event_count += 1  # 이벤트 카운트 증가
            
            # 상대 경로로 변환하여 로그 출력
            rel_path = os.path.relpath(event_path, Config.BASE_PATH)
            # print(f"스냅샷 큐에 추가됨 ({self.event_count}번째 이벤트): {rel_path}")
            
            self.queue.put(event_path, timeout=1.0)
        except queue.Full:
            print(f"큐가 가득 참 - 이벤트 무시됨: {event_path}")

    def on_modified(self, event):
        if event.is_directory:
            return
        
        if event.src_path.endswith(Config.SUPPORTED_EXTENSIONS):
            self._handle_file_event(event.src_path, '수정')
    
    def on_created(self, event):
        if event.is_directory:
            return
            
        if event.src_path.endswith(Config.SUPPORTED_EXTENSIONS):
            self._handle_file_event(event.src_path, '생성')

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
    
    # 스냅샷 큐 및 워커 초기화 (8개의 워커 생성)
    snapshot_queue = queue.Queue(maxsize=Config.QUEUE_SIZE)
    snapshot_worker = SnapshotWorker(snapshot_queue, num_workers=8)
    
    # 이벤트 핸들러 및 옵저버 설정
    event_handler = CodeChangeHandler(snapshot_queue)
    observer = Observer()
    
    for watch_dir in watch_dirs:
        observer.schedule(event_handler, watch_dir, recursive=True)
        print(f"디렉토리 감시 추가: {watch_dir}")
    
    # 워커와 옵저버 시작
    snapshot_worker.start()
    observer.start()
    
    try:
        print("모든 workspace 디렉토리 감시 시작...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n종료 중...")
        observer.stop()
        snapshot_worker.stop()
        print("감시 종료")
    
    observer.join()

if __name__ == "__main__":
    start_watching()