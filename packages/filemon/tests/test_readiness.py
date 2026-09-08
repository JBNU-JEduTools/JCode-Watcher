import urllib.error
import urllib.request

from app.readiness import ReadinessState, start_readiness_server


def test_readiness_stays_closed_until_filemon_initialization_finishes():
    state = ReadinessState()
    server = start_readiness_server(0, state)
    port = server.server_address[1]
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/ready"):
            raise AssertionError("초기화 전에 readiness가 성공했습니다.")
    except urllib.error.HTTPError as exc:
        assert exc.code == 503

    state.mark_ready()
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/ready") as response:
        assert response.status == 200
        assert response.read() == b"READY\n"

    state.mark_not_ready()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/ready"):
            raise AssertionError("종료 중 readiness가 성공했습니다.")
    except urllib.error.HTTPError as exc:
        assert exc.code == 503
    finally:
        server.shutdown()
        server.server_close()
