"""inotify 관련 유틸리티 함수"""
import os
from src.utils.logger import get_logger

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
                logger.info(f"Inotify {name}: {value}")
        except FileNotFoundError:
            logger.info(f"Inotify {name} 파일이 없음: {path}")
        except Exception as e:
            logger.info(f"Inotify {name} 확인 실패: {e}")
            
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
                
        logger.info(f"현재 inotify watch 수: {total_watches}")
    except Exception as e:
        logger.info(f"현재 inotify watch 수 확인 실패: {e}")

# 이전 함수는 유지하되 로깅 전용 함수를 따로 만듦
def get_inotify_status():
    """시스템의 inotify 상태를 확인하는 함수
    
    Returns:
        dict: inotify 상태 정보를 담은 딕셔너리
    """
    status = {}
    
    # 시스템 전체 설정 확인
    inotify_files = {
        'max_user_instances': '/proc/sys/fs/inotify/max_user_instances',
        'max_user_watches': '/proc/sys/fs/inotify/max_user_watches'
    }
    
    for name, path in inotify_files.items():
        try:
            with open(path, 'r') as f:
                status[name] = int(f.read().strip())
        except (FileNotFoundError, Exception):
            status[name] = None
            
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
                
        status['current_watches'] = total_watches
    except Exception:
        status['current_watches'] = None
        
    return status 