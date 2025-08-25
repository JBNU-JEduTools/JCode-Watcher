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

### 유저랜드(파이썬)

`src/` 디렉토리 내의 주요 컴포넌트들은 다음과 같습니다:

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


### 커널랜드(bpf)
eBPF를 시작하기전에 chatgpt 및 공식문서등을 통해 eBPF의 **제약**에 대해 상세하게 알아보세요. 크기 제한 및 verifier를 통과하기 위해서 몇가지 트릭들이 사용됩니다.

#### 가벼운 실행
bpf에 대한 수정은 프로덕션 프로젝트에서 직접 적용하고 수정하기 까다롭습니다.
간단한 파이썬 프로젝트를 생성하고 `apt install python3-bpfcc`로 의존성을 설치한 후 다음과 같은 파이썬 코드로 부터 시작하세요. 점차 테스트하고 완성하여 기존 프로젝트에 c코드를 붙여넣기 하세요.

```
# bpf_text는 기존처럼 파일로 읽거나 아니면 python코드에 string으로 정의해도 됩니다.
b = BPF(text=bpf_text)
b.attach_tracepoint(tp="sched:sched_process_exec", fn_name="trace_exec")

def print_event(cpu, data, size):
    event = b["events"].event(data)
    output = {
        "pid": event.pid,
        "command": event.comm.decode('utf-8').rstrip('\x00'),
        "container_id": event.container_id.decode('utf-8').rstrip('\x00')
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

#### 데이터구조

watcher-procmon에서 다루는 주요 데이터는 다음과같습니다. 이는 eBPF의 프로그램 스택 크기 제한을 우회하기 위함입니다. 대충 봐도 eBPF의 제한인 512B 를 훨씬 넘습니다. 
```
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
이는 BPF_PERCPU_ARRAY(tmp_array, struct data_t, 1);를 활용해 512B제한보다 더 큰 공간을 먼저 마련하고 필요한 데이터를 획득할때마다 이곳에 데이터를 복사하여 넣는 식으로 프로그램을 운영합니다.


#### 핸들러 정의
현재 bpf는 총 4개의 handler(bpf 프로그램)이 tailcall로 이어진 형태입니다. 이또한 ebpf의 스택 제한인 512B을 우회하고, 핸들러 분할을 통해서 verifier를 더 쉽게 통과하기 위함입니다.

bpf에 각 4가지의 핸들러를 정의한후 프로세스가 시작되는 타이밍(sched:sched_process_exec)에 init핸들러를 실행합니다. bcc를 이용해 정의한 테일콜에 의해서 각 핸들러가 순차적으로 실행됩니다.

// 첫 번째 핸들러: 호스트네임 검증 및 PID 설정
// 두 번째 핸들러: 바이너리 경로 수집
// 세 번째 핸들러: CWD 수집
// 네 번째 핸들러: 명령줄 인수 수집

각 핸들러는 데이터를 모아서 `BPF_HASH(process_data, u32, struct data_t);`에 pid를 키로하여 데이터를 저장합니다. 호스트는 프로세스당 고유의 pid하나를 할당하므로 어떤 컨테이너에서든 실행하더라도 항상 식별가능합니다. 프로세스가 종료되는 타이밍(sched_process_exit)에는 exit handler를 통해서 pid를 얻고 hash에 접근하여 저장된 데이터와 exit코드를 가지고 유저랜드에 반환합니다.

#### 디렉터리 경로 재구성

각 핸들러는 ctx를 통해서 현재 프로세스의 컨텍스트를 얻습니다. 컨텍스트로부터 PID를 획득할수있고
PID를 통해서 task struct를 얻습니다. task struct는 리눅스의 프로세스 제어 블록(PCB)입니다.
procmon에서 필요한 데이터는 모두 이 task_struct를 통해 획득합니다.
get_dentry_path라는 인라인 함수는 경로를 재구성하기 위한 함수입니다. 
현재 프로세스의 CWD가 /home/ubuntu/workspace라면 dentry를 획득하면 workspace라는 문자열과 상위 디렉터리인 ubuntu를 가르키는 연결리스트 구성입니다. 이 경로는 char배열의 마지막 요소부터 채워넣습니다.
이는 ebpf에서 쉽게 verifier에 통과하기 위한 전략입니다. buf는 충분히 여유로운 크기이기때문에 경로가 완성되면 ['\0', '\0', .... '/', 'h','o','m','e' ...] 과 같은 배열일것입니다.
파이썬은 항상 ctypes를 기반으로 데이터를 읽기때문에 '\0'을 만나면 문자열의 끝이라 고생각하고 더이상 글자를 읽지 않습니다. 우리는 이를 문자열이라 생각하지 않고 char배열이라고 생각합니다. 파이썬에서는 
`bytes(struct.binary_path[struct.binary_path_offset :])`와 같은 코드로 배열을 슬라이싱하여 첫번째 문자에서 앞의 널문자를 제거합니다.

#### 커널 안에서 print
아무리 수집한 데이터를 파이썬에서 출력해도 원인을 찾지 못하는경우가 있습니다.
커널에서 프린트하는 방법은 bpf_printk(또는 bpf_trace_printk) 함수를 활용해야합니다. 이또한 eBPF의 제약안에 있으므로, 컴파일타임에 고정되는 상수여야합니다.
bpf_printk()의 결과는 터미널에 바로 출력되지 않습니다. 커널 trace_pipe 에서 확인해야합니다.
sudo cat /sys/kernel/debug/tracing/trace_pipe 으로 데이터를 확인할 수 있습니다.


### 배포 및 컨테이너화

이미지 및 패키지
python3-bpfcc는 프로젝트에서 주로 사용하는 bpf도구입니다. 이는 시스템의 커널 버전과 맞물려있어 uv패키지로 다루기 힘듭니다. apt를 이용해 다운받아야합니다. 
로컬 패키지와 가상환경 패키지를 통합하기위해 RUN uv venv --system-site-packages /opt/venv
system-site-packages를 이용합니다. bpfcc는 가상환경이아닌 시스템에서 찾습니다.

컴포즈
wathcer-procmon은 컨테이너로 배포되지만 호스트에 바운드된 어플리케이션입니다. 호스트의 커널 데이터에 접근할수있도록 직접 볼륨마운트합니다. 
      - /sys/kernel/debug:/sys/kernel/debug:ro
      - /lib/modules:/lib/modules:ro
      - /usr/src:/usr/src:ro
컨테이너에서 PID는 네임스페이스(namespace)로 격리됩니다. 하지만 호스트 수준에서 모든 컨테이너들의 프로세스를 구분해야하므로  pid: host 를 설정하여 이를 우회합니다.

또한 컨테이너에서 ebpf를 실행하기 위한 권한인
    cap_drop:
      - ALL
    cap_add:
      - SYS_ADMIN
을 추가하여 통제합니다.
