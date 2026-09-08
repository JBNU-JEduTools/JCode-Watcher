# Watcher PostgreSQL 배포

Watcher의 신규 이벤트는 빈 PostgreSQL 데이터베이스에 저장합니다. 기존 SQLite는 과거 기록 보관본이며 새 API에 연결하거나 PostgreSQL로 복사하지 않습니다.

## 배포 순서

1. `watcher-postgres-app` Secret의 `uri`에 CNPG가 제공하는 `postgresql://` 연결 문자열을 설정합니다. Backend와 Alembic이 이를 psycopg 드라이버 URL로 정규화합니다.
2. 확인된 commit 이미지 digest를 `deploy/set-image-digests.py`로 dev overlay에 기록합니다.
3. `deploy/deploy.sh dev`를 실행합니다. 이 스크립트는 Backend를 내리고 `alembic upgrade head` Job을 완료한 뒤 Backend와 수집기를 올립니다.
4. Snapshot, Build, Run 등록·조회와 `/ready`, Pod 재시작 후 데이터 유지를 확인합니다.
5. 같은 digest를 production overlay에 기록하고 `deploy/deploy.sh production`을 실행합니다.

Backend와 migration Job에는 SQLite PVC를 마운트하지 않습니다. PostgreSQL 연결 실패 시 `/ready`만 실패하며 `/health`는 프로세스 상태를 계속 반환합니다.

최초 production 전환에서는 기존 수집기를 먼저 중단하고 SQLite 백업을 완료한 뒤 배포합니다. 새 Backend가 준비되기 전에 구형 수집기를 다시 시작하지 않습니다.

Filemon과 Procmon은 강의 Namespace의 `jcode.io/course-id` annotation을 읽어 `course_id`를 결정합니다. 이 권한은 `watcher-course-metadata-reader` ClusterRole의 Namespace `get`으로 제한됩니다.

수집 이벤트는 전송 전에 노드별 hostPath의 `event-spool.db`에 기록됩니다. Backend 장애나 수집기 재시작 후에도 같은 `event_id`로 배치 재전송되며, Backend는 배치를 한 트랜잭션으로 저장합니다. 해당 노드가 유실되면 미전송 이벤트도 함께 유실될 수 있으므로 노드 폐기 전 spool 잔여량을 확인합니다.

Production Filemon snapshot 볼륨은 Longhorn `watcher-filemon-pvc`를 사용합니다. dev overlay는 같은 PVC 선언의 StorageClass와 크기만 `nfs-dev`, 5Gi로 변경합니다.

Production Filemon은 공유 NFS에서 원격 Pod의 쓰기가 inotify로 전달되지 않는 제약을 피하기 위해 단일 Deployment로 실행합니다. 전체 NFS를 순회하지 않고 V2 불변 경로인 `사용자 작업공간/assignment-<id>` 아래의 지원 소스 파일만 5초 간격으로 열어 NFS 속성 캐시를 갱신한 뒤 비교합니다. 최초 스캔은 기준 상태만 만들며 이후 생성·수정·삭제부터 수집합니다.

`deploy/deploy.sh`는 과거 Filemon DaemonSet을 제거한 뒤 단일 Deployment를 적용합니다. 여러 Filemon 인스턴스를 동시에 실행하면 같은 NFS 이벤트를 중복 저장할 수 있으므로 replica 수는 1이고 교체 방식은 `Recreate`입니다.

Filemon의 `/ready`는 감시 스레드와 이벤트 재전송 루프가 시작된 뒤에만 200을 반환합니다. `/metrics`는 liveness와 메트릭 수집용이며 readiness 기준으로 사용하지 않습니다.

Filemon과 Procmon 로그 및 spool은 노드별 hostPath에 분리합니다. 로그는 파일당 10MiB, 백업 5개로 순환하며 기존 로그 PVC를 다시 마운트하지 않습니다. 기존 PVC는 이 매니페스트에서 삭제하지 않습니다.

## SQLite 보관 경계

- 기존 PVC와 PV는 삭제하지 않습니다.
- SQLite를 신규 Watcher의 읽기 또는 쓰기 대상으로 설정하지 않습니다.
- 과거 기록이 필요할 때만 관리자용 일회성 조회 Pod로 보관본을 엽니다.
- PostgreSQL 전환 이후 신규 기록의 유일한 원본은 PostgreSQL입니다.
