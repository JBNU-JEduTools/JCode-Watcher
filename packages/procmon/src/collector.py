import os
import asyncio
import threading
import logging
import ctypes
from typing import Optional, Any

from bcc import BPF
from .models import ProcessStruct
from .utils.logger import get_logger


class Collector:
    """
    프로세스 이벤트 수집기 (얇은 클래스/핸들)
    - BPF 프로그램 로드/어태치
    - perf buffer 콜백 → asyncio.Queue 전달
    - 폴링 스레드 라이프사이클 관리
    """

    def __init__(
        self,
        event_queue: asyncio.Queue,
        loop: asyncio.AbstractEventLoop,
        program_path: str,
        *,
        page_cnt: int = 64,
        poll_timeout_ms: int = 100,
    ) -> None:
        # 외부 주입 필수 자원
        self.event_queue: asyncio.Queue = event_queue
        self.loop: asyncio.AbstractEventLoop = loop
        self.program_path: str = program_path

        # BPF / 폴링 설정
        self.page_cnt: int = page_cnt
        self.poll_timeout_ms: int = poll_timeout_ms

        # 내부 상태
        self.logger = get_logger("collector")
        self.bpf: Optional[BPF] = None
        self.running_event: threading.Event = threading.Event()
        self.polling_thread: Optional[threading.Thread] = None
        self.dropped_count: int = 0
        self.lost_count: int = 0

    # -------- Public API --------

    @classmethod
    def start(
        cls,
        event_queue: asyncio.Queue,
        loop: asyncio.AbstractEventLoop,
        program_path: str,
        *,
        page_cnt: int = 64,
        poll_timeout_ms: int = 100,
    ) -> "Collector":
        """
        Collector 인스턴스를 완전히 시작된 상태로 반환한다.
        (부분 초기화 상태를 외부에 노출하지 않음)
        """
        self = cls(
            event_queue=event_queue,
            loop=loop,
            program_path=program_path,
            page_cnt=page_cnt,
            poll_timeout_ms=poll_timeout_ms,
        )
        self._load_bpf_program()
        self._start_polling()
        self.logger.info(
            "수집기 시작 완료",
            page_cnt=self.page_cnt,
            poll_timeout_ms=self.poll_timeout_ms,
        )
        return self

    def stop(self) -> None:
        """이벤트 수집 중지 및 리소스 정리"""
        try:
            self._stop_polling()
        finally:
            # BPF cleanup (가능한 경우)
            if self.bpf and hasattr(self.bpf, "cleanup"):
                try:
                    self.bpf.cleanup()  # type: ignore[attr-defined]
                except Exception as e:
                    self.logger.warning("BPF 정리 오류", error=str(e))
            self.logger.info(
                "수집기 중지 완료",
                dropped_count=self.dropped_count,
                lost_count=self.lost_count,
            )

    def __enter__(self) -> "Collector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    @property
    def is_running(self) -> bool:
        """수집 실행 상태"""
        return bool(
            self.running_event.is_set()
            and self.polling_thread
            and self.polling_thread.is_alive()
        )

    # -------- Internal: BPF setup / callbacks --------

    def _load_bpf_program(self) -> None:
        """BPF 프로그램 로드/어태치 및 perf buffer 설정"""
        if not os.path.isfile(self.program_path):
            raise FileNotFoundError(
                f"BPF 소스 파일을 찾을 수 없음: {self.program_path}"
            )

        self.logger.info("BPF 프로그램 로드 시작", program_path=self.program_path)
        with open(self.program_path, "r", encoding="utf-8") as f:
            bpf_text = f.read()

        self.bpf = BPF(text=bpf_text)

        # tail call용 프로그램들 로드 (핸들러 이름은 bpf.c와 일치해야 함)
        handlers = [
            self.bpf.load_func("init_handler", BPF.TRACEPOINT),
            self.bpf.load_func("binary_handler", BPF.TRACEPOINT),
            self.bpf.load_func("cwd_handler", BPF.TRACEPOINT),
            self.bpf.load_func("args_handler", BPF.TRACEPOINT),
        ]

        # prog_array에 fd 대입 (인덱스는 bpf.c의 TAIL_CALL 인덱스와 일치해야 함)
        prog_array = self.bpf.get_table("prog_array")
        for idx, handler in enumerate(handlers):
            prog_array[ctypes.c_int(idx)] = ctypes.c_int(handler.fd)

        # 트레이스포인트 어태치 (핸들러명은 eBPF 쪽과 매칭)
        self.bpf.attach_tracepoint(
            tp="sched:sched_process_exec", fn_name="init_handler"
        )
        self.bpf.attach_tracepoint(
            tp="sched:sched_process_exit", fn_name="exit_handler"
        )

        # perf buffer 콜백 등록
        self.bpf["events"].open_perf_buffer(
            self._event_callback,
            lost_cb=self._lost_callback,
            page_cnt=self.page_cnt,
        )

        self.logger.info("BPF 프로그램 로드 완료 및 트레이스포인트 연결됨")

    def _event_callback(self, cpu: int, data: Any, size: int) -> None:
        """BPF 이벤트 콜백: 커널 구조체 → Process → asyncio.Queue put"""
        try:
            raw_struct = ctypes.cast(data, ctypes.POINTER(ProcessStruct)).contents
            # asyncio 루프 스레드에서 안전하게 enqueue
            self.loop.call_soon_threadsafe(self._enqueue_on_loop, raw_struct)
        except Exception as e:
            self.logger.error("콜백 오류", error=str(e), exc_info=True)

    def _lost_callback(self, cpu: int, lost: int) -> None:
        """BCC가 보고하는 유실 이벤트 카운터 콜백"""
        self.lost_count += int(lost)
        # 과도한 로그 방지: 256번마다 1회
        if (self.lost_count & 0xFF) == 1:
            self.logger.warning("이벤트 유실 경고", cpu=cpu, lost_count=self.lost_count)

    def _enqueue_on_loop(self, ev: Any) -> None:
        """루프 스레드에서 호출되어 Queue에 넣는다 (가득 차면 드롭 카운트 증가)"""
        try:
            self.event_queue.put_nowait(ev)
        except asyncio.QueueFull:
            self.dropped_count += 1
            if (self.dropped_count & 0xFF) == 1:
                self.logger.warning("큐 가득참 경고", dropped_count=self.dropped_count)

    # -------- Internal: polling thread --------

    def _start_polling(self) -> None:
        """폴링 스레드 시작"""
        if self.running_event.is_set():
            return
        self.running_event.set()
        self.polling_thread = threading.Thread(
            target=self._run_polling,
            name="bpf-poller",
            daemon=True,
        )
        self.polling_thread.start()
        self.logger.info("폴링 스레드 시작됨")

    def _stop_polling(self) -> None:
        """폴링 스레드 중지"""
        if not self.running_event.is_set():
            return
        self.running_event.clear()
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=1.0)
        self.logger.info("폴링 스레드 중지됨")

    def _run_polling(self) -> None:
        """BPF perf buffer 폴링 루프 (정지 반응성을 위해 타임아웃 사용)"""
        if not self.bpf:
            self.logger.error("BPF 프로그램이 로드되지 않음")
            return

        self.logger.info("폴링 루프 시작", timeout_ms=self.poll_timeout_ms)
        while self.running_event.is_set():
            try:
                # 타임아웃(ms): stop() 호출 시 최대 이 시간 내로 깨어나 종료
                self.bpf.perf_buffer_poll(timeout=self.poll_timeout_ms)
            except Exception as e:
                # running 상태에서만 오류 로그 (정지 중 예외는 무시)
                if self.running_event.is_set():
                    self.logger.error("폴링 오류", error=str(e), exc_info=True)
                break
        self.logger.info("폴링 루프 종료됨")
