import os
import asyncio
import threading
import logging
import ctypes
from typing import Optional, Any
from bcc import BPF
from models.process import ProcessStruct

class Collector:
    """프로세스 이벤트 수집기 - BPF 프로그램 관리, 이벤트 처리, 폴링을 통합"""
    
    def __init__(self, event_queue: asyncio.Queue):
        self.event_queue = event_queue
        self.logger = logging.getLogger(__name__)
        self._loop = asyncio.get_running_loop()
        
        # BPF 관련
        self.bpf: Optional[BPF] = None
        
        # 폴링 관련
        self._running = False
        self._polling_thread: Optional[threading.Thread] = None
        
        self.logger.info("[초기화] Collector 초기화 완료")
        
    def start(self) -> None:
        """이벤트 수집 시작"""
        try:
            # BPF 프로그램 로드 및 설정
            self._load_bpf_program()
            
            # 폴링 시작
            self._start_polling()
            
            self.logger.info("[시작] 이벤트 수집 시작됨")
            
        except Exception as e:
            self.logger.error(f"[오류] 이벤트 수집 시작 실패: {e}")
            self.stop()
            raise
            
    def stop(self) -> None:
        """이벤트 수집 중지"""
        try:
            self._stop_polling()
            self.logger.info("[종료] 이벤트 수집 중지됨")
        except Exception as e:
            self.logger.error(f"[오류] 이벤트 수집 중지 중 오류: {e}")
            
    def _load_bpf_program(self) -> None:
        """BPF 프로그램 로드 및 설정"""
        self.logger.info("[BPF] 프로그램 로드 시작")
        
        # BPF 파일 읽기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        program_path = os.path.join(current_dir, "bpf.c")
        
        with open(program_path, 'r') as f:
            bpf_text = f.read()
        
        # BPF 컴파일 및 로드
        self.bpf = BPF(text=bpf_text)
        
        # 핸들러 설정
        handlers = [
            self.bpf.load_func("init_handler", BPF.TRACEPOINT),
            self.bpf.load_func("binary_handler", BPF.TRACEPOINT),
            self.bpf.load_func("cwd_handler", BPF.TRACEPOINT),
            self.bpf.load_func("args_handler", BPF.TRACEPOINT)
        ]
        
        prog_array = self.bpf.get_table("prog_array")
        for idx, handler in enumerate(handlers):
            prog_array[idx] = handler
            
        # 트레이스포인트 어태치
        self.bpf.attach_tracepoint(tp="sched:sched_process_exec", fn_name="init_handler")
        self.bpf.attach_tracepoint(tp="sched:sched_process_exit", fn_name="exit_handler")
            
        # 이벤트 콜백 연결
        self.bpf["events"].open_perf_buffer(self._event_callback)
        
        self.logger.info("[BPF] 프로그램 로드 및 설정 완료")
        
    def _event_callback(self, cpu: int, data: Any, size: int) -> None:
        """BPF 이벤트 콜백"""
        try:
            # 커널 구조체를 파이썬 객체로 변환
            raw_struct = ctypes.cast(data, ctypes.POINTER(ProcessStruct)).contents
            process_event = raw_struct.to_event()
            
            # 이벤트 큐에 전달
            self._loop.call_soon_threadsafe(
                self.event_queue.put_nowait,
                process_event
            )
        except Exception as e:
            self.logger.error(f"[오류] 콜백 처리 중 오류: {e}")
            
    def _start_polling(self) -> None:
        """폴링 쓰레드 시작"""
        if self._running:
            return
            
        self._running = True
        self._polling_thread = threading.Thread(
            target=self._run_polling,
            daemon=True
        )
        self.logger.info("[시작] BPF 폴링 쓰레드 시작")
        self._polling_thread.start()
        
    def _stop_polling(self) -> None:
        """폴링 중지"""
        if not self._running:
            return
            
        self._running = False
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=1.0)
        self.logger.info("[종료] BPF 폴링 중지")
        
    def _run_polling(self) -> None:
        """BPF 이벤트 폴링 실행"""
        if not self.bpf:
            self.logger.error("[오류] BPF 프로그램이 로드되지 않음")
            raise RuntimeError("BPF program not loaded")
            
        self.logger.info("[실행] BPF 이벤트 폴링 시작")
        
        while self._running:
            try:
                self.bpf.perf_buffer_poll()
            except KeyboardInterrupt:
                self.logger.info("[종료] 키보드 인터럽트로 인한 폴링 종료")
                break
            except Exception as e:
                if self._running:
                    self.logger.error(f"[오류] BPF 폴링 중 오류 발생: {e}")
                break
                
    @property
    def is_running(self) -> bool:
        """수집 실행 상태"""
        return self._running and self._polling_thread and self._polling_thread.is_alive()
        
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()