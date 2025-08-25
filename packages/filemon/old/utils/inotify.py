"""inotify 관련 유틸리티 함수"""
import os
from old.utils.logger import get_logger

logger = get_logger(__name__)

def log_inotify_status():
    """시스템의 inotify 상태를 확인하고 로깅하는 함수"""
    # 시스템 전체 설정 확인
    inotify_files = {
        'max_user_instances': '/proc/sys/fs/inotify/max_user_instances',
        'max_user_watches': '/proc/sys/fs/inotify/max_user_watches'
    }
    
    for name, path in inotify_files.items():
        try:
            with open(path, 'r') as f:
                value = int(f.read().strip())
                logger.info(f"Inotify status - type: {name}, value: {value}")
        except FileNotFoundError:
            logger.info(f"Inotify file not found - type: {name}, path: {path}")
        except Exception as e:
            logger.info(f"Inotify check failed - type: {name}, error: {str(e)}")
            
    # 현재 프로세스의 watch 수 확인
    try:
        pid = os.getpid()
        proc_fd_dir = f"/proc/{pid}/fd"
        total_watches = 0
        
        for fd in os.listdir(proc_fd_dir):
            try:
                fdinfo_path = f"/proc/{pid}/fdinfo/{fd}"
                with open(fdinfo_path) as f:
                    content = f.read()
                    if "inotify" in content:
                        watches = sum(1 for line in content.split('\n') if line.startswith('inotify'))
                        total_watches += watches
            except (FileNotFoundError, PermissionError):
                continue
                
        logger.info(f"Current inotify watches - count: {total_watches}")
    except Exception as e:
        logger.info(f"Watch count check failed - error: {str(e)}") 