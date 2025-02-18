"""
파일 시스템 감시 메인 모듈
watchdog과 asyncio를 사용하여 특정 디렉토리의 파일 변경을 감시
"""
import asyncio
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from .config import Config
from .file_filter import FileFilter

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class SnapshotManager:
    """스냅샷 관리 클래스"""
    
    @staticmethod
    def save_snapshot(file_path: str) -> None:
        """파일 스냅샷 저장"""
        source_path = Path(file_path)
        
        # 경로에서 필요한 정보 추출
        # 예: /watcher/codes/ai-1-202012180/config/workspace/hw1/test.c
        parts = source_path.parts
        try:
            # class_div_student 형식: ai-1-202012180
            class_div_student = parts[3]
            class_info = class_div_student.split('-')
            if len(class_info) != 3:
                raise ValueError(f"잘못된 클래스-분반-학번 형식: {class_div_student}")
                
            course = class_info[0]      # ai
            division = class_info[1]     # 1
            student_id = class_info[2]   # 202012180
            class_div = f"{course}-{division}"  # ai-1
            
            hw_dir = parts[6]     # hw1
            filename = source_path.name  # test.c
        except (IndexError, ValueError) as e:
            logging.error(f"잘못된 파일 경로 형식: {file_path} - {str(e)}")
            return
            
        # 타임스탬프 생성 (YYYYMMDD_HHMMSS 형식)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 스냅샷 저장 경로 생성
        # 수업분반/과제명/학번/파일명/타임스탬프
        snapshot_dir = Path(Config.SNAPSHOT_PATH) / class_div / hw_dir / student_id / filename.replace('.', '_')
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        # 스냅샷 파일 경로
        snapshot_path = snapshot_dir / f"{timestamp}{source_path.suffix}"
        
        try:
            # 파일 복사
            shutil.copy2(source_path, snapshot_path)
            logging.info(f"스냅샷 저장 완료: {snapshot_path}")
        except Exception as e:
            logging.error(f"스냅샷 저장 실패: {e}")

class EventQueue:
    """이벤트 큐 관리 클래스"""
    
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.queue = asyncio.Queue(maxsize=Config.QUEUE_SIZE)
        self.loop = loop
        
    def put_event_threadsafe(self, event_type: str, file_path: str) -> None:
        """외부 스레드에서 이벤트를 큐에 추가"""
        try:
            self.loop.call_soon_threadsafe(
                self.queue.put_nowait,
                (event_type, file_path)
            )
        except asyncio.QueueFull:
            logging.warning("이벤트 큐가 가득 찼습니다.")
            
    async def put_event(self, event_type: str, file_path: str) -> None:
        """비동기 컨텍스트에서 이벤트를 큐에 추가"""
        try:
            await self.queue.put((event_type, file_path))
        except asyncio.QueueFull:
            logging.warning("이벤트 큐가 가득 찼습니다.")
            
    async def get_event(self) -> tuple[str, str]:
        """이벤트를 큐에서 가져옴"""
        return await self.queue.get()
        
    def task_done(self) -> None:
        """이벤트 처리 완료 표시"""
        self.queue.task_done()

class FileChangeHandler(FileSystemEventHandler):
    """파일 시스템 이벤트 핸들러"""
    
    def __init__(self, event_queue: EventQueue):
        self.event_queue = event_queue
        self.file_filter = FileFilter()
        
    def on_modified(self, event: FileModifiedEvent):
        """파일 수정 이벤트 처리 (외부 스레드에서 호출)"""
        if event.is_directory:
            return
            
        file_path = str(event.src_path)
        if self.file_filter.should_ignore(file_path):
            return
            
        # 스레드 안전한 방식으로 이벤트 추가
        self.event_queue.put_event_threadsafe("modified", file_path)
        logging.info(f"파일 수정 감지: {file_path}")

async def process_events(event_queue: EventQueue):
    """이벤트 처리 코루틴"""
    while True:
        try:
            event_type, file_path = await event_queue.get_event()
            # 파일 I/O 작업을 스레드 풀에서 실행
            await asyncio.to_thread(SnapshotManager.save_snapshot, file_path)
            logging.info(f"이벤트 처리 완료: {event_type} - {file_path}")
        except Exception as e:
            logging.error(f"이벤트 처리 중 오류 발생: {e}")
        finally:
            event_queue.task_done()

async def main():
    """메인 함수"""
    loop = asyncio.get_running_loop()
    
    # 이벤트 큐 및 핸들러 설정
    event_queue = EventQueue(loop)
    handler = FileChangeHandler(event_queue)
    observer = Observer()
    
    # 감시할 디렉토리 설정
    base_path = Path(Config.BASE_PATH)
    watch_pattern = Config.WATCH_PATTERN 
    homework_pattern = Config.HOMEWORK_PATTERN
    
    # 모든 대상 디렉토리 찾기
    for path in base_path.glob(watch_pattern):
        if path.is_dir():
            for hw_dir in path.glob(homework_pattern):
                if hw_dir.is_dir():
                    observer.schedule(handler, str(hw_dir), recursive=True)
                    logging.info(f"감시 시작: {hw_dir}")
    
    # 옵저버 시작
    observer.start()
    logging.info("파일 시스템 감시 시작")
    
    try:
        # 이벤트 처리 코루틴 시작
        await process_events(event_queue)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("파일 시스템 감시 중단")
    
    observer.join()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("프로그램 종료")
