#!/usr/bin/env bash
set -euo pipefail

target=${1:?usage: deploy/deploy.sh <dev|production>}
case "$target" in
  dev) namespace=dev ;;
  production) namespace=watcher ;;
  *) echo "target must be dev or production" >&2; exit 2 ;;
esac

kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
kubectl get secret watcher-postgres-app -n "$namespace" >/dev/null
db_url=$(kubectl get secret watcher-postgres-app -n "$namespace" -o jsonpath='{.data.uri}' | base64 --decode)
if [[ "$db_url" != postgresql://* && "$db_url" != postgresql+psycopg://* ]]; then
  echo "watcher-postgres-app Secret의 uri는 PostgreSQL 연결 문자열이어야 합니다." >&2
  exit 1
fi
unset db_url
if [[ "$target" == "dev" ]]; then
  for legacy in watcher-proc; do
    if kubectl get deployment "$legacy" -n "$namespace" >/dev/null 2>&1; then
      kubectl scale deployment/"$legacy" -n "$namespace" --replicas=0
      kubectl rollout status deployment/"$legacy" -n "$namespace" --timeout=5m
    fi
  done
fi
kubectl delete daemonset watcher-filemon -n "$namespace" --ignore-not-found --wait=true
if kubectl get deployment watcher-backend -n "$namespace" >/dev/null 2>&1; then
  kubectl scale deployment/watcher-backend -n "$namespace" --replicas=0
  kubectl rollout status deployment/watcher-backend -n "$namespace" --timeout=5m
fi
kubectl delete job watcher-backend-migration -n "$namespace" --ignore-not-found --wait=true
kubectl apply -k "deploy/migration/overlays/${target}"
for _ in $(seq 1 60); do
  if kubectl get secret watcher-harbor-registry-secret -n "$namespace" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
kubectl get secret watcher-harbor-registry-secret -n "$namespace" >/dev/null
kubectl wait -n "$namespace" --for=condition=complete job/watcher-backend-migration --timeout=5m

kubectl apply -k "deploy/overlays/${target}"
kubectl rollout status -n "$namespace" deployment/watcher-backend --timeout=5m
kubectl rollout status -n "$namespace" deployment/watcher-filemon --timeout=5m
kubectl rollout status -n "$namespace" daemonset/watcher-procmon --timeout=5m
