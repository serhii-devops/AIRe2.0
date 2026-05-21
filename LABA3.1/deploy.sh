
kubectl apply -f manifests/observability.yaml --dry-run=client -o yaml | grep -A 5 "kind: Namespace" | kubectl apply -f -
kubectl apply -f manifests/deployment.yaml --dry-run=client -o yaml | grep -A 5 "kind: Namespace" | kubectl apply -f -


kubectl apply -f manifests/observability.yaml

kubectl apply -f manifests/ollama.yaml

kubectl wait --for=condition=ready pod -l app=ollama -n kagent-system --timeout=300s || true

kubectl wait --for=condition=complete job/ollama-pull-model -n kagent-system --timeout=600s

kubectl apply -f manifests/deployment.yaml

kubectl wait --for=condition=ready pod -l app=sre-agent -n kagent-system --timeout=120s

kubectl apply -f manifests/agent-crd.yaml

