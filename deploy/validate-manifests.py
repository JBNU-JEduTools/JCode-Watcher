#!/usr/bin/env python3
import argparse
from pathlib import Path

import yaml


def documents(path: Path) -> list[dict]:
    return [
        item for item in yaml.safe_load_all(path.read_text(encoding="utf-8")) if item
    ]


def find(items: list[dict], kind: str, name: str) -> dict:
    return next(
        item
        for item in items
        if item["kind"] == kind and item["metadata"]["name"] == name
    )


def env(container: dict) -> dict[str, dict]:
    return {item["name"]: item for item in container.get("env", [])}


def validate_release(path: Path, environment: str) -> None:
    items = documents(path)
    namespace = "dev" if environment == "dev" else "watcher"
    backend = find(items, "Deployment", "watcher-backend")["spec"]["template"]["spec"]
    backend_deployment = find(items, "Deployment", "watcher-backend")
    assert backend_deployment["spec"]["replicas"] == (
        1 if environment == "dev" else 2
    )
    backend_container = backend["containers"][0]
    db = env(backend_container)["DB_URL"]["valueFrom"]["secretKeyRef"]
    assert db == {"name": "watcher-postgres-app", "key": "uri"}
    assert backend_container["readinessProbe"]["httpGet"]["path"] == "/ready"
    assert backend_container["livenessProbe"]["httpGet"]["path"] == "/health"
    assert all(
        mount.get("mountPath") != "/app/data"
        for mount in backend_container.get("volumeMounts", [])
    )

    binding_name = f"watcher-course-metadata-reader-{environment}"
    binding = find(items, "ClusterRoleBinding", binding_name)
    assert binding["subjects"] == [
        {
            "kind": "ServiceAccount",
            "name": "watcher-course-reader",
            "namespace": namespace,
        }
    ]
    collector_kinds = {
        "watcher-filemon": "Deployment",
        "watcher-procmon": "DaemonSet",
    }
    for name, kind in collector_kinds.items():
        pod = find(items, kind, name)["spec"]["template"]["spec"]
        assert pod["serviceAccountName"] == "watcher-course-reader"
        container = pod["containers"][0]
        collector_env = env(container)
        assert collector_env["JCODE_ENVIRONMENT"]["value"] == (
            "dev" if environment == "dev" else "prod"
        )
        assert collector_env["SPOOL_PATH"]["value"] == (
            "/var/lib/jcode-watcher/spool/event-spool.db"
        )
        spool_volume = next(
            volume
            for volume in pod["volumes"]
            if volume["name"] in {"spool", "spool-volume"}
        )
        assert spool_volume["hostPath"]["type"] == "DirectoryOrCreate"
        collector = "filemon" if name == "watcher-filemon" else "procmon"
        assert spool_volume["hostPath"]["path"] == (
            f"/var/lib/jcode-watcher/{collector}-spool"
        )
        assert any(
            mount["mountPath"] == "/var/lib/jcode-watcher/spool"
            for mount in container["volumeMounts"]
        )

    filemon = find(items, "Deployment", "watcher-filemon")
    assert filemon["spec"]["replicas"] == 1
    assert filemon["spec"]["strategy"]["type"] == "Recreate"
    filemon_container = filemon["spec"]["template"]["spec"]["containers"][0]
    assert filemon_container["readinessProbe"]["httpGet"] == {
        "path": "/ready",
        "port": "http-ready",
    }
    assert env(filemon_container)["LOG_BACKUP_COUNT"]["value"] == "5"
    assert env(filemon_container)["FILE_WATCH_MODE"]["value"] == "polling"
    assert env(filemon_container)["FILE_POLL_INTERVAL_SECONDS"]["value"] == "5"
    if environment == "dev":
        assert filemon["spec"]["template"]["spec"]["nodeSelector"] == {
            "env": "dev"
        }
    filemon_logs = next(
        volume
        for volume in filemon["spec"]["template"]["spec"]["volumes"]
        if volume["name"] == "logs-volume"
    )
    assert filemon_logs["hostPath"] == {
        "path": "/var/lib/jcode-watcher/filemon-logs",
        "type": "DirectoryOrCreate",
    }
    snapshot_volume = next(
        volume
        for volume in filemon["spec"]["template"]["spec"]["volumes"]
        if volume["name"] == "snapshot-volume"
    )
    expected_snapshot_claim = "watcher-filemon-pvc"
    assert (
        snapshot_volume["persistentVolumeClaim"]["claimName"]
        == expected_snapshot_claim
    )
    pvc_names = {
        item["metadata"]["name"]
        for item in items
        if item["kind"] == "PersistentVolumeClaim"
    }
    assert "watcher-filemon-pvc" in pvc_names
    assert "watcher-filemon-logs-pvc" not in pvc_names

    procmon = find(items, "DaemonSet", "watcher-procmon")
    procmon_pod = procmon["spec"]["template"]["spec"]
    procmon_container = procmon_pod["containers"][0]
    assert env(procmon_container)["LOG_BACKUP_COUNT"]["value"] == "5"
    procmon_logs = next(
        volume for volume in procmon_pod["volumes"] if volume["name"] == "logs"
    )
    assert procmon_logs["hostPath"] == {
        "path": "/var/lib/jcode-watcher/procmon-logs",
        "type": "DirectoryOrCreate",
    }
    assert "watcher-procmon-logs-pvc" not in pvc_names

    for item in items:
        pod_spec = item.get("spec", {}).get("template", {}).get("spec", {})
        for container in pod_spec.get("containers", []):
            assert not container.get("image", "").startswith("harbor.jbnu.ac.kr/")


def validate_migration(path: Path) -> None:
    job = find(documents(path), "Job", "watcher-backend-migration")["spec"]["template"][
        "spec"
    ]
    container = job["containers"][0]
    assert container["command"] == ["alembic", "-c", "alembic.ini", "upgrade", "head"]
    assert env(container)["DB_URL"]["valueFrom"]["secretKeyRef"] == {
        "name": "watcher-postgres-app",
        "key": "uri",
    }
    assert not container.get("volumeMounts")
    assert not job.get("volumes")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("environment", choices=("dev", "production"))
    parser.add_argument("release", type=Path)
    parser.add_argument("migration", type=Path)
    args = parser.parse_args()
    validate_release(args.release, args.environment)
    validate_migration(args.migration)


if __name__ == "__main__":
    main()
