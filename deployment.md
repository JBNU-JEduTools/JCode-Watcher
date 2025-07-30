## Watcher 시스템 배포 가이드

### 🎯 배포 목표

JCode 플랫폼의 학습자 모니터링을 위한 Watcher 시스템을 Kubernetes 클러스터에 배포합니다. 이 시스템은 학생들의 코딩 활동(파일 변경, 프로세스 실행)을 실시간으로 추적하여 학습 분석 데이터를 수집합니다.

### 🏗️ 시스템 아키텍처 이해

우리가 배포할 서비스는 총 3개입니다:

**1. watcher-backend**

- 역할: 모든 모니터링 데이터를 수집하는 중앙 API 서버
- 포트: 3000번 (HTTP API)
- 스토리지: SQLite 데이터베이스 저장용 PVC
- 배포 방식: Deployment로 배포

**2. watcher-filemon**

- 역할: 각 노드에서 학생 워크스페이스의 파일 변경을 감지
- 포트: 9090번 (Prometheus 메트릭)
- 스토리지: 파일 스냅샷 저장용 PVC + WebIDE workspace NFS 볼륨 접근 권한
- 배포 방식: 모든 워커 노드에 1개씩 배포

**3. watcher-procmon**

- 역할: 각 노드에서 gcc, python 등의 프로세스 실행을 eBPF로 추적
- 포트: 9090번 (Prometheus 메트릭)
- 특수 권한: hostPID=true, SYS_ADMIN/SYS_PTRACE capabilities 필요
- 배포 방식: 모든 워커 노드에 1개씩 배포

### ✅ 1단계: 사전 설정

#### 1. 네임스페이스 생성

Watcher 시스템 전용 네임스페이스를 먼저 생성합니다:

```bash
kubectl create namespace watcher
```

#### 2. Longhorn 스토리지 확인

우리 시스템은 여러 Web IDE 컨테이너에서 작업하는 모든 코드들의 내용을 Longhorn 분산 스토리지를 통해 저장합니다. 다음 명령어로 Longhorn 스토리지를 확인하세요.

```bash
kubectl get storageclass longhorn
```

정상적인 경우 다음과 같이 출력됩니다:

```
NAME                 PROVISIONER          RECLAIMPOLICY   VOLUMEBINDINGMODE   ALLOWVOLUMEEXPANSION
longhorn (default)   driver.longhorn.io   Delete          Immediate           true
```

만약 "not found" 오류가 나면 Longhorn을 먼저 구성해야합니다.

#### 3. 학생용 WebIDE 워크스페이스 공유 볼륨 준비

filemon 서비스는 학생들이 WebIDE에서 작성하는 코드가 저장된 워크스페이스 볼륨에 접근해야 합니다. 이 볼륨은 WebIDE 컨테이너와 모니터링 서비스들이 함께 사용하는 공유 스토리지입니다.

**먼저 기존 워크스페이스 볼륨 확인:**

```bash
# JCode 플랫폼에서 사용 중인 워크스페이스 PVC 확인
kubectl get pvc -A | grep -E "(workspace|jcode|webide)"
```

만약 기존에 JCode 플랫폼이 운영 중이고 워크스페이스 PVC가 이미 존재한다면, 해당 PVC 이름을 확인하고 **7단계로 건너뛰세요**.

**기존 볼륨이 없는 경우에만** 다음 단계를 수행하여 새로운 워크스페이스 볼륨을 생성합니다:

#### 4. WebIDE 워크스페이스 PVC 생성

```yaml
# jcode-vol-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: jcode-vol-pvc
  namespace: watcher
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: longhorn
  resources:
    requests:
      storage: 10Gi
```

#### 5. RWX 볼륨 바인딩을 위한 임시 Pod 생성

Longhorn에서 RWX 볼륨을 정상적으로 바인딩하기 위해 임시 클라이언트 Pod를 실행합니다:

```yaml
# minimal-rwx-client.yaml
apiVersion: v1
kind: Pod
metadata:
  name: minimal-rwx-client
  namespace: watcher
spec:
  containers:
    - name: minimal-client
      image: busybox:latest
      command: ["sh", "-c", "echo 'Minimal RWX client running'; sleep infinity"]
      volumeMounts:
        - name: shared-data
          mountPath: /data
  volumes:
    - name: shared-data
      persistentVolumeClaim:
        claimName: jcode-vol-pvc
```

#### 6. 순서대로 실행

```bash
# PVC 먼저 생성
kubectl apply -f jcode-vol-pvc.yaml

# PVC 바인딩 확인
kubectl get pvc -n watcher jcode-vol-pvc

# Pod 생성 (PVC 참조)
kubectl apply -f minimal-rwx-client.yaml
```

#### 7. 볼륨 바인딩 최종 확인

```bash
# PV 생성 확인 (새로 생성한 경우)
kubectl get pv | grep jcode-vol-pvc

# 또는 기존 워크스페이스 PVC 확인 (기존 볼륨 사용 시)
kubectl get pvc -n <jcode-namespace> <기존-workspace-pvc-이름>
```

정상적인 경우 다음과 같이 출력됩니다:

```
NAME           STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS
jcode-vol-pvc  Bound    pvc-5ba357bc-eaca-4585-8e2a-a19ff156887b   10Gi       RWX            longhorn
```

### 📦 2단계: 코드 준비 및 Docker 이미지 빌드

#### 최신 코드 가져오기

먼저 프로젝트 디렉토리로 이동하여 최신 변경사항을 가져옵니다:

```bash
git clone https://github.com/JBNU-JEduTools/JCode-Watcher.git
cd JCode-Watcher
```

#### Docker 이미지 빌드

**사전 준비**: 아래 명령어에서 `<VERSION_TAG>`를 원하는 버전으로 변경하세요:

- `<VERSION_TAG>`: 이미지 버전 태그 (예: v1.0.0, 2024.01.15 등)

각 서비스를 순서대로 빌드합니다. 빌드 시간은 서비스당 약 2-3분 소요됩니다:

```bash
cd packages/backend
docker build -t harbor.jbnu.ac.kr/jdevops/watcher-backend:<VERSION_TAG> .

cd ../filemon
docker build -t harbor.jbnu.ac.kr/jdevops/watcher-filemon:<VERSION_TAG> .

cd ../procmon
docker build -t harbor.jbnu.ac.kr/jdevops/watcher-procmon:<VERSION_TAG> .
```

**빌드 완료 확인:**

```bash
docker images | grep harbor.jbnu.ac.kr/jdevops/watcher

# 성공하면 다음 메시지가 출력됩니다:
# harbor.jbnu.ac.kr/jdevops/watcher-backend    <VERSION_TAG>
# harbor.jbnu.ac.kr/jdevops/watcher-filemon    <VERSION_TAG>
# harbor.jbnu.ac.kr/jdevops/watcher-procmon    <VERSION_TAG>
```

### 🚀 3단계: Harbor 레지스트리에 이미지 업로드

#### Harbor 로그인

```bash
docker login harbor.jbnu.ac.kr

# 성공하면 다음 메시지가 출력됩니다:
# Login Succeeded
```

#### 이미지 업로드

빌드된 3개 이미지를 모두 레지스트리에 업로드합니다:

```bash
docker push harbor.jbnu.ac.kr/jdevops/watcher-backend:<VERSION_TAG>
docker push harbor.jbnu.ac.kr/jdevops/watcher-filemon:<VERSION_TAG>
docker push harbor.jbnu.ac.kr/jdevops/watcher-procmon:<VERSION_TAG>

# 성공하면 다음 메시지가 출력됩니다:
# <VERSION_TAG>: digest: sha256:abc123... size: 1234
```

**업로드 확인:**
Harbor 웹 인터페이스(`https://harbor.jbnu.ac.kr`)에서 `jdevops` 프로젝트를 확인하여 3개 이미지가 업로드되었는지 확인하세요.

### ☸️ 4단계: Kubernetes 클러스터에 배포

#### Harbor 레지스트리 인증 설정

Harbor 레지스트리 접근 권한을 설정합니다:

```bash
 kubectl create secret docker-registry watcher-harbor-registry-secret \
  --docker-server=harbor.jbnu.ac.kr \
  --docker-username=<실제사용자명> \
  --docker-password=<실제비밀번호> \
  -n watcher
```

위 명령어에서 `<실제사용자명>`과 `<실제비밀번호>`를 본인의 Harbor 계정 정보로 바꿔서 입력하세요.

**시크릿 생성 확인:**

```bash
kubectl get secret -n watcher watcher-harbor-registry-secret
```

#### 스토리지 리소스 생성

서비스가 사용할 영구 볼륨을 먼저 생성합니다:

```bash
# 백엔드 데이터베이스용 스토리지 (10GB)
kubectl apply -f packages/backend/watcher-backend-pvc.yaml
```

```bash
# 파일 스냅샷 저장용 스토리지 (30GB)
kubectl apply -f packages/filemon/watcher-filemon-pvc.yaml
```

**PVC 생성 확인:**

```bash
kubectl get pvc -n watcher
```

다음과 같이 2개의 PVC가 `Bound` 상태여야 합니다:

```
NAME                           STATUS   VOLUME    CAPACITY   ACCESS MODES   STORAGECLASS
watcher-backend-pvc            Bound    pvc-...   10Gi       RWX            longhorn
watcher-filemon-storage-pvc    Bound    pvc-...   30Gi       RWX            longhorn
```

#### filemon 서비스를 위한 NFS 마운트 설정

filemon 서비스는 `학생용 WebIDE 워크스페이스`에서 파일 변경을 실시간으로 감지하기 위해 inotify를 사용합니다.
Kubernetes에서 볼륨 접근 방식에 따라 파일 변경 감지 동작이 달라집니다:

**PersistentVolumeClaim (CSI 기반)**

- 각 Pod가 독립적인 마운트 인스턴스를 할당받음
- 동일 노드 내에서도 Pod 간 파일시스템 이벤트가 실시간 공유되지 않음

**NFS 볼륨 마운트**

- 여러 Pod가 동일한 네트워크 파일시스템을 직접 공유
- 한 Pod의 파일 변경이 같은 노드의 다른 Pod에서 즉시 감지됨

따라서 실시간 파일 변경 감지가 핵심인 filemon 서비스는 NFS 볼륨 마운트 방식을 사용합니다.

**1. 현재 jcode-vol-pvc의 NFS 정보 확인:**

```bash
kubectl get pvc jcode-vol-pvc -n watcher -o jsonpath='{.spec.volumeName}'

# pvc-5ba357bc-eaca-4585-8e2a-a19ff156887b
```

**2. Longhorn NFS 주소 구성 규칙:**
위에서 얻은 volumeHandle을 사용하여 NFS 정보를 구성합니다:

```yaml
nfs:
  server: "<volumeHandle>.longhorn-system.svc.cluster.local"
  path: "/<volumeHandle>"
# 실제 예시 (volumeHandle이 "pvc-5ba357bc-eaca-4585-8e2a-a19ff156887b"인 경우):
# nfs:
#  server: "pvc-5ba357bc-eaca-4585-8e2a-a19ff156887b.longhorn-system.svc.cluster.local"
#  path: "/pvc-5ba357bc-eaca-4585-8e2a-a19ff156887b"
```

**3. watcher-filemon.yaml 수정:**
`packages/filemon/watcher-filemon.yaml` 파일에서 jcode-vol 볼륨 설정을 다음과 같이 수정하세요:

```yaml
spec:
  containers:
    - name: watcher-filemon
      image: harbor.jbnu.ac.kr/jdevops/watcher-filemon:20250729-1
  #...
  volumes:
    - name: jcode-vol
      nfs:
        server: "pvc-5ba357bc-eaca-4585-8e2a-a19ff156887b.longhorn-system.svc.cluster.local"
        path: "/pvc-5ba357bc-eaca-4585-8e2a-a19ff156887b"
  #...
```

#### 배포 전 매니페스트 설정 점검

배포하기 전에 각 서비스의 매니페스트 파일이 올바르게 설정되어 있는지 확인하고 필요시 수정하세요.

**1. watcher-backend 환경변수 (`packages/backend/watcher-backend.yaml`)**

```yaml
env:
  - name: DB_URL
    value: "sqlite:////app/data/database.db" # SQLite 데이터베이스 경로
```

- `DB_URL`: 백엔드에서 사용할 데이터베이스 연결 정보
- SQLite 파일은 PVC 마운트된 `/app/data` 디렉토리에 저장됩니다

**2. watcher-filemon 환경변수 (`packages/filemon/watcher-filemon.yaml`)**

```yaml
env:
  - name: WATCHER_LOG_LEVEL
    value: "INFO" # 로그 레벨: DEBUG, INFO, WARNING, ERROR
  - name: WATCHER_API_URL
    value: "http://watcher-backend-service.watcher.svc.cluster.local:3000"
```

- `WATCHER_LOG_LEVEL`: 파일 모니터링 로그 상세도 설정
- `WATCHER_API_URL`: 백엔드 API 쿠버네티스 내부 서버 주소

**3. watcher-procmon 환경변수 (`packages/procmon/watcher-procmon.yaml`)**

```yaml
env:
  - name: API_ENDPOINT
    value: "http://watcher-backend-service.watcher.svc.cluster.local:3000"
  - name: LOG_LEVEL
    value: "INFO" # 로그 레벨: DEBUG, INFO, WARNING, ERROR
```

- `API_ENDPOINT`: 백엔드 API 쿠버네티스 내부 서버 주소
- `LOG_LEVEL`: 프로세스 모니터링 로그 상세도 설정

> 쿠버네티스 내부 URL에 대한 자세한 내용은 [공식문서](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)를 참고하세요.

**환경변수 확인:**
모든 서비스가 `watcher` 네임스페이스를 사용하므로 서비스 URL이 올바른지 확인하세요:

```yaml
# watcher-filemon.yaml
- name: WATCHER_API_URL
  value: "http://watcher-backend-service.watcher.svc.cluster.local:3000"

# watcher-procmon.yaml
- name: API_ENDPOINT
  value: "http://watcher-backend-service.watcher.svc.cluster.local:3000"
```

**이미지 태그 확인:**
각 YAML 파일에서 이미지 태그가 올바른지 확인하세요:

```yaml
# 현재 설정된 태그
image: harbor.jbnu.ac.kr/jdevops/watcher-backend:20250729-1
image: harbor.jbnu.ac.kr/jdevops/watcher-filemon:20250729-1
image: harbor.jbnu.ac.kr/jdevops/watcher-procmon:20250729-1

# 필요시 본인이 빌드한 태그로 변경
image: harbor.jbnu.ac.kr/jdevops/watcher-backend:<VERSION_TAG>
```

#### 애플리케이션 서비스 배포

이제 실제 Watcher 서비스들을 배포합니다:

```bash
# 백엔드 API 서버 배포 (포트 3000)
kubectl apply -f packages/backend/watcher-backend.yaml
kubectl apply -f packages/filemon/watcher-filemon.yaml
kubectl apply -f packages/procmon/watcher-procmon.yaml
```

### ✅ 4단계: 배포 상태 확인

#### 전체 리소스 상태 확인

```bash
kubectl get all -n watcher
```

정상 배포된 경우 다음과 같이 출력됩니다:

```
NAME                                 READY   STATUS    RESTARTS   AGE
pod/watcher-backend-xxx-xxx          1/1     Running   0          2m
pod/watcher-filemon-xxx              1/1     Running   0          1m
pod/watcher-procmon-xxx              1/1     Running   0          1m

NAME                               TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
service/watcher-backend-service    ClusterIP   10.96.xxx.xxx   <none>        3000/TCP   2m
service/watcher-filemon           ClusterIP   10.96.xxx.xxx   <none>        9090/TCP   1m
service/watcher-procmon           ClusterIP   10.96.xxx.xxx   <none>        9090/TCP   1m

NAME                             DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR   AGE
daemonset.apps/watcher-filemon   3         3         3       3            3           <none>          1m
daemonset.apps/watcher-procmon   3         3         3       3            3           <none>          1m

NAME                              READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/watcher-backend   1/1     1            1           2m
```

#### 개별 서비스 로그 확인

각 서비스가 정상 동작하는지 로그를 확인합니다:

```bash
# 백엔드 API 서버 로그
kubectl logs -n watcher -l app=watcher-backend --tail=20
```

정상적인 경우 다음과 같은 로그가 출력됩니다:

```
Server starting on port 3000
Database initialized
API endpoints ready
```

```bash
# 파일 모니터링 서비스 로그
kubectl logs -n watcher -l app=watcher-filemon --tail=20
```

```bash
# 프로세스 모니터링 서비스 로그
kubectl logs -n watcher -l app=watcher-procmon --tail=20
```

#### 서비스 연결 테스트

백엔드 API가 정상 작동하는지 테스트합니다:

```bash
kubectl run test-pod --image=curlimages/curl -i --tty --rm -- \
  curl http://watcher-backend-service.watcher.svc.cluster.local:3000/health
```

정상적인 경우 다음과 같은 응답이 옵니다:

```json
{ "status": "healthy", "timestamp": "2024-01-01T00:00:00Z" }
```

### 📊 5단계: 모니터링 및 메트릭 확인

#### Prometheus 메트릭 접근

파일 모니터링 서비스의 메트릭을 로컬에서 확인할 수 있습니다:

```bash
kubectl port-forward -n watcher service/watcher-filemon 9090:9090
```

다른 터미널에서 브라우저를 열고 `http://localhost:9090/metrics`에 접속하세요. 다음과 같은 메트릭들을 확인할 수 있습니다:

```
# HELP file_events_total Total number of file events detected
# TYPE file_events_total counter
file_events_total{event_type="create"} 25
file_events_total{event_type="modify"} 142
file_events_total{event_type="delete"} 8

# HELP process_events_total Total number of process events detected
# TYPE process_events_total counter
process_events_total{process_name="gcc"} 15
process_events_total{process_name="python3"} 23
```

#### ServiceMonitor 확인 (Prometheus Operator 사용 시)

클러스터에 Prometheus Operator가 설치되어 있다면 자동으로 메트릭이 수집됩니다:

```bash
kubectl get servicemonitor -n watcher
```
