import os
import logging
import threading
import asyncio
from typing import Optional, Any
from bcc import BPF
from .event import RawBpfStruct
import ctypes

class BPFCollector:
    """BPF 이벤트 수집 담당"""
    def __init__(self, event_queue: asyncio.Queue):
        self.event_queue = event_queue
        self.bpf: Optional[BPF] = None
        self.logger = logging.getLogger(__name__)
        self._running = True
        self._loop = asyncio.get_running_loop()
        self.logger.info("[초기화] BPFCollector 초기화 완료")

    def event_callback(self, cpu: int, data: Any, size: int) -> None:
        """BPF 이벤트 콜백
        
        커널에서 받은 이벤트를 파이썬 이벤트 객체로 변환하여 큐에 전달합니다.
        """
        try:
            # 커널 구조체를 파이썬 객체로 변환
            raw_struct = ctypes.cast(data, ctypes.POINTER(RawBpfStruct)).contents
            # 구조체를 이벤트로 변환
            raw_event = raw_struct.to_event()
            
            # 이벤트 큐에 전달
            self._loop.call_soon_threadsafe(
                self.event_queue.put_nowait,
                raw_event
            )
        except Exception as e:
            self.logger.error(f"[오류] 콜백 처리 중 오류: {e}")

    def load_program(self) -> None:
        """BPF 프로그램 로드 및 설정"""
        try:
            self.logger.info("[BPF] 프로그램 로드 시작")
            current_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(current_dir, 'program.c'), 'r') as f:
                bpf_text = f.read()
            
            self.bpf = BPF(text=bpf_text)
            
            # 핸들러 설정 (새로운 순서)
            handlers = [
                self.bpf.load_func("init_handler", BPF.TRACEPOINT),
                self.bpf.load_func("binary_handler", BPF.TRACEPOINT),
                self.bpf.load_func("cwd_handler", BPF.TRACEPOINT),
                self.bpf.load_func("args_handler", BPF.TRACEPOINT)
            ]
            
            prog_array = self.bpf.get_table("prog_array")
            for idx, handler in enumerate(handlers):
                prog_array[idx] = handler
            
            self.bpf["events"].open_perf_buffer(self.event_callback)
            self.bpf.attach_tracepoint(tp="sched:sched_process_exec", fn_name="init_handler")
            self.bpf.attach_tracepoint(tp="sched:sched_process_exit", fn_name="exit_handler")
            self.logger.info("[BPF] 프로그램 로드 완료")
            
        except Exception as e:
            self.logger.error(f"[오류] BPF 프로그램 로드 실패: {e}")
            raise

    def start_polling(self) -> None:
        """폴링 쓰레드 시작"""
        self._running = True
        self._polling_thread = threading.Thread(
            target=self.run_polling,
            daemon=True
        )
        self.logger.info("[시작] BPF 폴링 쓰레드 시작")
        self._polling_thread.start()

    def stop_polling(self) -> None:
        """폴링 중지 및 정리"""
        self._running = False
        if hasattr(self, '_polling_thread'):
            self._polling_thread.join(timeout=1.0)
        self.logger.info("[종료] BPF 폴링 중지")

    def run_polling(self) -> None:
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
                self.logger.error(f"[오류] BPF 폴링 중 오류 발생: {e}") 