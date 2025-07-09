# 컨테이너 모니터링을 위한 Docker 실행 옵션 가이드

## 요구사항
다른 컨테이너를 감시하는 bpf프로세스 또한 컨테이너로 배포되어야 함

## 권장 실행 명령어 (최소 권한)
```bash
docker run -it \
  --cap-drop=ALL \
  --cap-add=SYS_ADMIN \
  --cap-add=SYS_PTRACE \
  --pid=host \
  -v /sys/kernel/debug:/sys/kernel/debug:ro \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  watcher-proc:latest
```



컨테이너 해시 관련 (kn->name)
cgroup의 leaf 디렉토리를 출력
docker: docker-9a879f2ecd371ce4724
kubernetes: cri-containerd-6cc798ea


sudo cat /sys/kernel/debug/tracing/trace_pipe


tailcall을 활용한 bpf 핸들러 분할/핸들러간 연결

