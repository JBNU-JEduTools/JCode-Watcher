from IPython import get_ipython
import os, socket, requests
from datetime import datetime

ip = get_ipython()
API_BASE = "http://watcher-backend-service.watcher.svc.cluster.local:3000"

def after_cell_exec(result=None):
    try:
        # ISO 8601 문자열 (예: 2025-10-22T20:31:55.613932)
        timestamp = datetime.now().isoformat()

        cwd = os.getcwd()
        hostname = socket.gethostname()
        parts = hostname.split('-')

        # 수업 / 분반 / 학번
        class_div  = parts[1] if len(parts) > 1 else 'unknown'
        hw_name    = parts[2] if len(parts) > 2 else 'unknown'
        student_id = parts[3] if len(parts) > 3 else 'unknown'

        # 실행 성공(0) / 실패(1)
        exit_code = 0 if (result and getattr(result, "success", False)) else 1

        # 코드 내용은 항상 비공개
        cmdline = "<unknown>"

        payload = {
            "timestamp": timestamp,       # ✅ 필드명 수정
            "exit_code": exit_code,
            "cmdline": cmdline,
            "cwd": cwd,
            "target_path": "ipykernel",
            "process_type": "python"
        }

        url = f"{API_BASE}/api/{class_div}/{hw_name}/{student_id}/logs/run"

        # 조용히 전송 (실패 시 무시)
        try:
            requests.post(url, json=payload, timeout=1)
        except Exception:
            pass

    except Exception as e:
        # Hook 내부 오류는 콘솔에 출력하지 않고 파일에만 기록
        with open("/tmp/jupyter_exec_error.log", "a", encoding="utf-8") as f:
            f.write(f"[HOOK][INTERNAL ERROR] {datetime.now().isoformat()} {type(e).__name__}: {e}\n")

ip.events.register('post_run_cell', after_cell_exec)
