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
      command: ["sh", "-c", "echo 'Minimal RWX client running'; sleep 3600"]
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
# 백엔드 API 서버 이미지 빌드
cd packages/backend
docker build -t harbor.jbnu.ac.kr/jdevops/watcher-backend:<VERSION_TAG> .
```

빌드가 성공하면 다음과 같은 메시지가 출력됩니다:

```
Successfully built abc123def456
Successfully tagged harbor.jbnu.ac.kr/jdevops/watcher-backend:<VERSION_TAG>
```

```bash
# 파일 모니터링 서비스 이미지 빌드 (inotify 기반)
cd ../filemon
docker build -t harbor.jbnu.ac.kr/jdevops/watcher-filemon:<VERSION_TAG> .
```

```bash
# 프로세스 모니터링 서비스 이미지 빌드 (eBPF 기반)
cd ../procmon
docker build -t harbor.jbnu.ac.kr/jdevops/watcher-procmon:<VERSION_TAG> .
```

**빌드 완료 확인:**

```bash
docker images | grep harbor.jbnu.ac.kr/jdevops/watcher
```

3개의 이미지가 모두 보여야 합니다:

```
harbor.jbnu.ac.kr/jdevops/watcher-backend    <VERSION_TAG>
harbor.jbnu.ac.kr/jdevops/watcher-filemon    <VERSION_TAG>
harbor.jbnu.ac.kr/jdevops/watcher-procmon    <VERSION_TAG>
```

### 🚀 2단계: Harbor 레지스트리에 이미지 업로드

#### Harbor 로그인

```bash
docker login harbor.jbnu.ac.kr
```

사용자명과 비밀번호를 입력하세요. 성공하면 다음 메시지가 출력됩니다:

```
Login Succeeded
```

#### 이미지 업로드

빌드된 3개 이미지를 모두 레지스트리에 업로드합니다:

```bash
docker push harbor.jbnu.ac.kr/jdevops/watcher-backend:<VERSION_TAG>
docker push harbor.jbnu.ac.kr/jdevops/watcher-filemon:<VERSION_TAG>
docker push harbor.jbnu.ac.kr/jdevops/watcher-procmon:<VERSION_TAG>
```

각 푸시가 완료되면 다음과 같은 메시지가 출력됩니다:

```
<VERSION_TAG>: digest: sha256:abc123... size: 1234
```

**업로드 확인:**
Harbor 웹 인터페이스(`https://harbor.jbnu.ac.kr`)에서 `jdevops` 프로젝트를 확인하여 3개 이미지가 업로드되었는지 확인하세요.

### ☸️ 3단계: Kubernetes 클러스터에 배포

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
kubectl apply -f packages/backend/k8s-pvc.yaml
```

```bash
# 파일 스냅샷 저장용 스토리지 (30GB)
kubectl apply -f packages/filemon/k8s-pvc.yaml
```

**PVC 생성 확인:**

```bash
kubectl get pvc -n watcher
```

다음과 같이 2개의 PVC가 `Bound` 상태여야 합니다:

```
NAME                           STATUS   VOLUME    CAPACITY   ACCESS MODES   STORAGECLASS
watcher-backend-pvc            Bound    pvc-...   10Gi       RWO            longhorn
watcher-filemon-storage-pvc    Bound    pvc-...   30Gi       RWX            longhorn
```

#### 애플리케이션 서비스 배포

이제 실제 Watcher 서비스들을 배포합니다:

```bash
# 백엔드 API 서버 배포 (포트 3000)
kubectl apply -f packages/backend/k8s.yaml
```

```bash
# 파일 모니터링 서비스 배포 (포트 9090, 모든 노드)
kubectl apply -f packages/filemon/k8s.yaml
```

```bash
# 프로세스 모니터링 서비스 배포 (포트 9090, 모든 노드)
kubectl apply -f packages/procmon/k8s.yaml
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

### 🔧 문제 해결 가이드

#### Pod가 Pending 상태인 경우

```bash
kubectl describe pod -n watcher <pod-name>
```

일반적인 원인:

- **PVC가 바인딩되지 않음**: Longhorn 설치 상태 확인
- **노드 리소스 부족**: `kubectl top nodes`로 리소스 사용량 확인
- **이미지 Pull 실패**: Harbor 시크릿 설정 확인

#### filemon Pod가 CrashLoopBackOff인 경우

NFS 볼륨 접근 권한 문제일 가능성:

```bash
kubectl exec -n watcher <filemon-pod> -- ls -la /watcher/codes
```

#### procmon Pod가 권한 오류로 실패하는 경우

eBPF 실행을 위한 커널 권한 문제:

```bash
kubectl exec -n watcher <procmon-pod> -- ls -la /sys/kernel/debug
```

### 🎉 배포 완료!

모든 단계가 성공적으로 완료되었다면 Watcher 시스템이 정상 동작합니다.

**최종 확인사항:**

- [ ] 3개 서비스 모두 Running 상태
- [ ] 백엔드 API 헬스체크 통과
- [ ] 메트릭 엔드포인트 접근 가능
- [ ] 로그에 오류 메시지 없음

이제 JCode 플랫폼의 학습자 활동이 실시간으로 모니터링됩니다!
