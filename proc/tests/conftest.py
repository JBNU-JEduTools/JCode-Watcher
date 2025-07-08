import pytest
from src.bpf.event import RawBpfEvent
from src.events.models import EventBuilder

@pytest.fixture
def raw_event():
    """기본 테스트용 RawBpfEvent fixture"""
    return RawBpfEvent(
        hostname="jcode-os-1-202012345-hash",
        binary_path="/usr/bin/gcc",
        command="gcc -o test test.c",
        pid=1234,
        ppid=1000,
        uid=1000,
        cwd="/home/test",
        args=["gcc", "-o", "test", "test.c"]
    )

@pytest.fixture
def event_builder(raw_event):
    """기본 테스트용 EventBuilder fixture"""
    return EventBuilder(base=raw_event)
