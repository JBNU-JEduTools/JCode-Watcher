# Watcher Procmon - 프로세스 실시간 감시 서비스

eBPF를 활용한 실시간 프로세스 모니터링 시스템입니다. 컨테이너 환경에서의 프로세스 실행을 감지하고, 컴파일러 및 Python 실행을 추적하여 코딩 활동 분석을 수행합니다.


## 1. 개요

### 프로젝트 소개
Watcher Procmon은 eBPF(Extended Berkeley Packet Filter)를 사용하여 리눅스 시스템에서 프로세스 실행을 실시간으로 모니터링하는 시스템입니다. 특히 교육 환경에서 학생들의 프로그래밍 활동을 추적하고 분석하는 데 최적화되어 있습니다.

### 주요 기능
- eBPF를 통한 실시간 프로세스 모니터링
- 컴파일러 감지 및 분석 (GCC, Clang, G++ 등)
- 빌드된 프로세스 실행 추적 (C/C++ 실행 파일, Python 스크립트)

## 2. 아키텍처

```

┌──────────────┐    ┌───────────┐    ┌──────────────────┐     ┌─────────────┐    ┌───────────┐
│ BPF Program  │──▶│ Collector │──▶ │  Event Queue     │──▶ │   Pipeline   │──▶│  Sender   │
│   (bpf.c)    │    │ (Python)  │    │ (asyncio.Queue)  │     │ (pipeline.py)│   │(sender.py)│
└──────────────┘    └───────────┘    └──────────────────┘     └──────────────┘   └─────┬─────┘
      │                                                                                │
  Captures                                                                           Sends
      │                                                                                │
      ▼                                                                                ▼
┌──────────────┐                                                                 ┌───────────┐
│Kernel Events │                                                                 │ HTTP POST │
│(exec, exit)  │                                                                 │ (to API)  │
└──────────────┘                                                                 └───────────┘
```

### 주요 컴포넌트 흐름
1.  **BPF Program (`bpf.c`)**: 커널에서 `exec`/`exit` 이벤트를 감지하여 `perf_buffer`를 통해 유저 공간으로 `ProcessStruct` 원시 데이터를 전송합니다.
2.  **Collector (`collector.py`)**: BPF 프로그램을 관리하고 커널로부터 받은 `ProcessStruct` 데이터를 `asyncio.Queue`에 넣습니다.
3.  **Event Queue (`asyncio.Queue`)**: 커널 이벤트와 파이프라인 처리 사이의 버퍼 역할을 합니다.
4.  **Pipeline (`pipeline.py`)**: 큐에서 이벤트를 가져와 처리하는 핵심 로직입니다. 내부에 여러 파서(`StudentParser`, `PathParser`, `FileParser`)와 `ProcessClassifier`를 사용하여 이벤트를 분석, 필터링하고 최종적으로 API로 전송할 `Event` 객체를 생성합니다.
5.  **Sender (`sender.py`)**: `Pipeline`이 생성한 `Event` 객체를 받아 백엔드 API 서버로 전송합니다.

## 3. 로컬 테스트 가이드

로컬 환경에서 `procmon`의 전체 흐름을 테스트하는 가이드입니다. 학생의 개발 환경(`code-server`)과 `procmon` 서비스를 모두 Docker로 실행하여 실제와 유사한 환경을 구성합니다.

### 1단계: 학생용 code-server 환경 구성
`procmon`이 감시할 대상인 학생의 워크스페이스를 `code-server` 컨테이너를 이용해 생성합니다. 이 컨테이너의 `hostname`은 `procmon`이 학생을 식별하는 기준이 됩니다.

1.  **학생별 디렉터리 생성**
    호스트 머신에 학생의 작업 공간으로 마운트할 디렉터리를 생성합니다. 디렉터리명은 `jcode` 컨테이너의 `hostname`과 일관성을 가지도록 구성합니다.
    ```bash
    # mkdir -p /workspace/{수업명}-{분반}-{학번}
    mkdir -p /workspace/class-1-202012345
    ```

2.  **code-server 컨테이너 실행**
    생성한 디렉터리를 마운트하고, 정해진 형식의 `hostname`을 지정하여 `code-server` 컨테이너를 실행합니다.
    ```bash
    sudo docker run -d \
      --name jcode-class-1-202012345 \
      -p 8080:8080 \
      -e PASSWORD="jcode" \
      -v /workspace/class-1-202012345/:/home/coder/project \
      --hostname jcode-class-1-202012345 \
      codercom/code-server:latest
    ```

### 2단계: Procmon 서비스 설정

1.  **소스코드 준비 및 의존성 설치**
    ```bash
    git clone https://github.com/JBNU-JEduTools/JCode-Watcher
    cd JCode-Watcher/packages/procmon
    uv sync
    ```

2.  **환경변수 설정**
    `procmon` 실행에 필요한 환경변수는 `docker-compose.yml`의 `environment` 섹션에서 설정합니다. 주요 변수는 다음과 같습니다.

| 변수명             | 설명                                  | 기본값                        |
| :----------------- | :------------------------------------ | :---------------------------- |
| `LOG_LEVEL`        | 로그 출력 레벨                        | `"INFO"`                      |
| `API_SERVER`       | 이벤트 전송 대상 API 서버 주소        | `"http://localhost:8000"`     |
| `METRICS_PORT`     | Prometheus 메트릭 노출 포트           | `3000`                        |
| `LOG_FILE_PATH`    | 로그 파일 경로 (컨테이너 내부)        | `"/app/logs/procmon.log"`     |
| `LOG_MAX_BYTES`    | 로그 파일 최대 크기 (바이트)          | `10485760` (10MB)             |
| `LOG_BACKUP_COUNT` | 보관할 최대 로그 파일 수 (0은 무제한) | `0`                           |


    실제 `docker-compose.yml` 적용 예시:
    ```yaml
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=DEBUG
      - API_SERVER=http://localhost:8000
    ```

### 3단계: Procmon 실행 및 유닛 테스트

-   **애플리케이션 실행 (통합 테스트)**
    `procmon`은 커널 이벤트에 의존하므로 Docker 환경에서 실행해야 합니다. Docker Compose를 사용하면 필요한 모든 권한과 설정을 포함하여 서비스를 쉽게 실행할 수 있습니다.
    ```bash
    # Docker Compose를 사용하여 서비스 빌드 및 실행
    docker-compose up --build
    ```

-   **유닛 테스트**
    개별 코드의 논리 검증을 위한 유닛 테스트는 로컬 개발 환경에서 `uv`를 통해 실행합니다.
    ```bash
    # 전체 유닛 테스트 실행
    uv run pytest
    ```

### 4단계: 동작 확인

1.  **Code-Server 접속**: 웹 브라우저에서 `http://localhost:8080`으로 접속하고, 비밀번호 `jcode`를 입력합니다.
2.  **테스트 파일 생성 및 컴파일**: `code-server`의 터미널에서 아래 명령어를 실행하여 컴파일 이벤트를 발생시킵니다.
    ```bash
    mkdir hw1
    cd hw1
    echo 'int main() { return 0; }' > test.c
    gcc test.c -o test_program
    ./test_program
    ```
3.  **로그 확인**: `docker-compose up`을 실행한 터미널에서 `procmon` 서비스의 로그를 확인합니다. 아래와 유사한 로그가 출력되면 정상적으로 동작하는 것입니다.
    ```log
    watcher-1  | 2025-00-00T05:56:43.405066Z [debug    ] 이벤트 생성됨                        [procmon.pipeline] class_div=class-1 homework_dir=hw1 process_type=ProcessType.GCC source_file=/home/coder/project/hw1/test.c student_id=202012345
    watcher-1  | 2025-00-00T05:56:44.946816Z [debug    ] 이벤트 생성됨                        [procmon.pipeline] class_div=class-1 homework_dir=hw1 process_type=ProcessType.USER_BINARY source_file=None student_id=202012345
    ```

## 5. 메트릭 수집 확인

`procmon` 서비스가 정상적으로 메트릭을 노출하는지 확인합니다.

1.  **Prometheus 메트릭 엔드포인트 접속**: 웹 브라우저 또는 `curl`을 사용하여 `http://localhost:3000/metrics`에 접속합니다.
    ```bash
    curl http://localhost:3000/metrics
    ```

2.  **주요 메트릭 확인**: 아래와 같은 메트릭들이 노출되는지 확인합니다.
    -   **하트비트 메트릭**: `poll_heartbeat_ts_seconds`, `loop_heartbeat_ts_seconds`
    -   **파이프라인 처리 이벤트 수**: `pipeline_events_total`
    -   **큐 상태 메트릭**: `queue_size_current`, `queue_events_dropped_total`
    -   **BPF 이벤트 수집 메트릭**: `bpf_events_collected_total`, `bpf_events_lost_total`

    예시:
    ```
    poll_heartbeat_ts_seconds{service="procmon"} 1.7561024651589966e+09
    loop_heartbeat_ts_seconds{service="procmon"} 1.7561024629578404e+09
    pipeline_events_total{result="nontarget",service="procmon"} 96.0
    ```

## 6. 개발 가이드 

### 유저랜드(Python)

`app/` 디렉토리 내의 주요 컴포넌트들은 다음과 같습니다:

-   **`collector.py`**: `bpf.c` eBPF 프로그램을 로드하고 커널로부터 이벤트를 수집하여 `asyncio.Queue`에 전달하는 역할을 합니다.
-   **`classifier.py`**: 프로세스의 바이너리 경로를 분석하여 `ProcessType` (예: GCC, Python)을 분류합니다.
-   **`file_parser.py`**: 컴파일러 또는 Python 스크립트의 명령줄 인자에서 소스 파일 경로를 파싱합니다.
-   **`path_parser.py`**: 파일 경로에서 과제 디렉토리(`hwN`) 정보를 추출합니다.
-   **`pipeline.py`**: `collector`로부터 받은 원시 프로세스 데이터를 `Event` 객체로 변환하는 핵심 파이프라인입니다. `classifier`, `path_parser`, `file_parser`, `student_parser`를 활용하여 데이터를 처리하고 필터링합니다.
-   **`sender.py`**: 처리된 `Event` 객체를 백엔드 API 서버로 전송합니다.
-   **`student_parser.py`**: 호스트 이름에서 학생 정보(학번, 과목-분반)를 파싱합니다.
-   **`models/`**: 애플리케이션 내에서 사용되는 데이터 모델(클래스)들을 정의합니다.
    -   `event.py`: 처리된 이벤트의 데이터 구조.
    -   `process.py`: 커널에서 수집된 프로세스 정보의 파이썬 객체 표현.
    -   `process_struct.py`: eBPF 프로그램과 통신하기 위한 C 구조체 정의.
    -   `process_type.py`: 프로세스 타입(GCC, PYTHON 등) 열거형 정의.
    -   `student_info.py`: 학생 정보 데이터 구조.


### 커널랜드(eBPF)

eBPF 개발을 시작하기 전, ChatGPT 또는 공식 문서 등을 통해 eBPF의 **제약 사항**을 확인하세요. 스택 크기 제한과 Verifier의 검증을 통과하기 위해 몇가지 트릭들이 사용됩니다.

#### 가벼운 실행

BPF 프로그램은 프로덕션 환경에 직접 적용하고 수정하기에 복잡성이 따릅니다. 따라서 독립된 Python 프로젝트에서 `apt install python3-bpfcc`로 의존성을 설치하고 아래와 같은 최소 기능 코드로 개발을 시작하는 것을 권장합니다. 점진적인 테스트를 통해 프로그램을 완성한 후, 기존 프로젝트에 통합하는 방식이 효율적입니다.

```python
from bcc import BPF
import json
import sys

bpf_text='''#include <uapi/linux/ptrace.h>

struct data_t {
    u32 pid;
};

BPF_PERF_OUTPUT(events);

int trace_exec(struct tracepoint__sched__sched_process_exec *ctx) {
    struct data_t data = {};

    // 현재 실행 중인 task의 PID 추출
    data.pid = bpf_get_current_pid_tgid() >> 32;

    // user-space로 전송
    events.perf_submit(ctx, &data, sizeof(data));

    return 0;
}'''

b = BPF(text=bpf_text)
b.attach_tracepoint(tp="sched:sched_process_exec", fn_name="trace_exec")

def print_event(cpu, data, size):
    event = b["events"].event(data)
    output = {
        "pid": event.pid,
    }
    print(json.dumps(output))

b["events"].open_perf_buffer(print_event)

print("프로세스 추적 중... Ctrl+C로 종료하세요.", file=sys.stderr)
while True:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        break
```

#### 데이터 구조

watcher-procmon에서 사용하는 주요 데이터 구조는 다음과 같습니다. 이 구조체는 eBPF의 스택 크기 제한(512B)을 초과하므로, 이를 우회하기 위한 설계가 적용되었습니다.

```c
struct data_t {
    u32 pid;
    u32 error_flags;
    char hostname[UTS_LEN];
    char binary_path[MAX_PATH_LEN];
    char cwd[MAX_PATH_LEN];
    char args[ARGSIZE];
    int binary_path_offset;
    int cwd_offset;
    u32 args_len;
    int exit_code;
};
```

이는 `BPF_PERCPU_ARRAY`를 활용해 512B보다 큰 임시 저장 공간을 확보하고, 필요한 데이터를 수집할 때마다 이 공간에 순차적으로 복사하는 방식으로 동작합니다.

#### 핸들러 정의

현재 BPF 프로그램은 총 네 개의 핸들러(BPF 프로그램)가 Tail Call로 연결된 구조입니다. 이러한 핸들러 분할 방식은 eBPF의 스택 제한을 우회하고, 각 핸들러의 복잡도를 낮춰 Verifier의 검증을 용이하게 하는 목적을 가집니다.

프로세스 생성 이벤트(sched:sched_process_exec)가 발생하면 첫 번째 핸들러가 실행되고, 이후 BCC 라이브러리를 통해 설정된 Tail Call에 의해 나머지 핸들러들이 순차적으로 호출됩니다. 이 흐름에서 첫 번째 핸들러는 호스트네임을 검증하고 PID를 설정하며, 두 번째 핸들러는 실행된 바이너리 경로를 수집합니다. 이어서 세 번째 핸들러가 현재 작업 디렉터리(CWD)를 수집하고, 마지막 네 번째 핸들러가 명령줄 인수를 수집합니다.

각 핸들러는 이렇게 수집한 데이터를 BPF_HASH(process_data, u32, struct data_t)에 PID를 키로 하여 저장합니다. 리눅스에서 호스트는 프로세스당 고유의 PID를 하나씩만 할당하므로, 어떤 컨테이너에서 실행되더라도 PID는 항상 유일하게 식별 가능합니다. 또한 프로세스가 종료되는 sched_process_exit 시점에는 exit 핸들러가 해당 프로세스의 PID를 얻어 BPF_HASH에서 데이터를 조회하고, 이 데이터를 종료 코드와 함께 유저랜드로 전송합니다.

#### 디렉터리 경로 재구성

`get_dentry_path` 인라인 함수는 dentry 구조체를 순회하며 파일 경로를 재구성하는 역할을 합니다. 예를 들어 현재 CWD가 `/home/ubuntu/workspace`일 경우, dentry는 'workspace'라는 이름과 상위 디렉터리('ubuntu')의 dentry를 가리키는 포인터로 구성됩니다.

이 함수는 경로를 재구성할 때, 제공된 char 배열의 끝에서부터 문자를 채워나가는 방식을 사용합니다. 이는 Verifier의 검증을 통과하기 위한 eBPF의 일반적인 기법 중 하나입니다. 경로 재구성이 완료된 버퍼는 `['\0', '\0', ..., '/', 'h', 'o', 'm', 'e', ...]`와 같은 형태를 가집니다.

유저랜드의 Python 코드는 ctypes를 통해 이 데이터를 읽는데, 선행하는 NULL 문자(`\0`) 때문에 일반적인 문자열 처리 방식으로는 전체 경로를 읽을 수 없습니다. 따라서 이를 char 배열로 간주하고, `bytes(struct.binary_path[struct.binary_path_offset :])`와 같이 실제 경로가 시작되는 offset부터 슬라이싱하여 올바른 경로 문자열을 얻습니다.

#### 커널 안에서 print

유저랜드에서 데이터를 분석하기 어려운 경우, 커널 레벨에서의 디버깅이 필요할 수 있습니다. 이때 `bpf_printk` (또는 `bpf_trace_printk`) 함수를 사용하여 커널 내부의 상태를 출력할 수 있습니다. 단, eBPF 제약으로 인해 포맷 문자열은 컴파일 타임에 상수로 결정되어야 합니다.

`bpf_printk`의 출력 결과는 표준 출력으로 표시되지 않으며, 커널의 trace_pipe를 통해 확인해야 합니다. `sudo cat /sys/kernel/debug/tracing/trace_pipe` 명령어로 실시간 출력을 확인할 수 있습니다.

#### 배포 및 컨테이너화

프로젝트의 핵심 도구인 `python3-bpfcc`는 시스템의 커널 버전에 의존성이 높아 일반적인 Python 패키지 매니저(uv)로 관리하기 어렵습니다. 따라서 `apt`와 같은 시스템 패키지 매니저를 통해 설치해야 합니다.

Docker 이미지 빌드 시, 시스템 레벨에 설치된 bpfcc와 가상 환경의 패키지를 함께 사용하기 위해 `RUN uv venv --system-site-packages /opt/venv` 명령을 실행합니다. 이 옵션을 통해 가상 환경 내에서도 시스템 사이트 패키지(system-site-packages)를 참조할 수 있으므로, bpfcc 라이브러리를 정상적으로 임포트할 수 있습니다.

watcher-procmon은 컨테이너로 배포되지만 호스트의 커널 데이터에 접근해야 하므로, 아래와 같이 주요 시스템 디렉터리를 컨테이너에 직접 볼륨 마운트합니다.
```yaml
    volumes:
      - /sys/kernel/debug:/sys/kernel/debug:ro
      - /lib/modules:/lib/modules:ro
      - /usr/src:/usr/src:ro
```

컨테이너가 호스트 수준의 PID 네임스페이스를 그대로 사용하도록 pid: host 옵션을 지정합니다. 이를 통해 컨테이너 내부에서 관찰되는 PID가 호스트와 동일하게 매핑되어, 프로세스 식별이 일관되게 유지됩니다.
마지막으로, 컨테이너 실행시 SYS_ADMIN를 추가(cap_add: [SYS_ADMIN])하여 eBPF 프로그램을 로딩할 수 있게 합니다.