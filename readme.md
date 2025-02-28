FILE_COUNT = 4096       # 동시에 생성·수정할 파일 개수
MODIFY_COUNT = 10    # 각 파일이 수정될 횟수
DELAY_BETWEEN_MODS = 0.1  # 각 수정 사이 지연(초)

================ Stress Test Complete ================
총 파일 개수: 4096
각 파일당 수정 횟수: 10
최종 총 수정 이벤트 수: 40960
실행 시간: 19.09초

할일
- gracefully shutdown
- 에러 핸들링


```bash
# 1. 기존 minikube 중지 (실행 중인 경우)
minikube stop

# 2. MTU 1450으로 설정하여 minikube 시작
minikube start --docker-opt="mtu=1450"

# 3. minikube docker daemon 환경 설정
eval $(minikube docker-env)

# 4. 이미지 빌드 (이미지가 minikube VM의 docker daemon에 직접 빌드됨)
docker build -t watcher-code:latest .

# 선택사항: MTU 설정 확인
minikube ssh "ip link show docker0"
```


port 
```
minikube kubectl -- port-forward  --address 0.0.0.0 svc/os-1-202012180 8080:8080
```