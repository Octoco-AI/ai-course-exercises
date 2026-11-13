"""Tests for block_mutating_ops.py.

Run either way from this directory:

    python3 -m unittest -v test_block_mutating_ops.py
    python3 -m pytest -q test_block_mutating_ops.py

When you add a read verb to the hook, add an ALLOW case here. When you find a
command the hook let through that it should not have, add a DENY case first.
"""

import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import block_mutating_ops as hook  # noqa: E402

HOOK = os.path.join(HERE, "block_mutating_ops.py")

ALLOW = [
    # kubectl reads
    "kubectl get pods -n payments",
    "kubectl -n payments get pods -o wide",
    "kubectl --context staging --namespace web describe deploy/api",
    "kubectl logs deploy/api --since=15m --tail=200",
    "kubectl top pods -n web",
    "kubectl get events --sort-by=.lastTimestamp",
    "kubectl rollout status deploy/api",
    "kubectl rollout history deploy/api",
    "kubectl auth can-i delete pods --as system:serviceaccount:ops:ops-reader",
    "kubectl config get-contexts",
    "kubectl diff -f manifests/",
    "kubectl explain deployment.spec.strategy",
    "k get nodes",
    "/usr/local/bin/kubectl get ns",
    "KUBECONFIG=~/.kube/ops-reader kubectl get pods",
    "kubectl get pods -o json | jq '.items[].metadata.name'",
    "kubectl get pods 2>&1 | grep -i crashloop",
    "kubectl get pods > /tmp/pods.txt",
    "timeout 30 kubectl get pods -w",
    "kubectl get pods -o name | xargs -n1 kubectl describe",
    "microk8s kubectl get pods",
    # helm reads
    "helm list -A",
    "helm status api -n web",
    "helm get values api -n web",
    "helm history api -n web",
    "helm diff upgrade api ./charts/api -f values-staging.yaml",
    "helm template api ./charts/api | kubectl diff -f -",
    "helm --kube-context staging -n web ls",
    "helm dependency list ./charts/api",
    # argocd reads
    "argocd app get payments-api",
    "argocd app list -o wide",
    "argocd app diff payments-api",
    "argocd app history payments-api",
    "argocd --grpc-web app get payments-api --refresh",
    "argocd app actions list payments-api",
    "argocd version --client",
    # aws reads
    "aws sts get-caller-identity",
    "aws --profile ops-reader cloudwatch describe-alarms --state-value ALARM",
    "aws cloudwatch describe-alarm-history --alarm-name orders-5xx --max-records 20",
    "aws cloudwatch get-metric-statistics --namespace AWS/RDS --metric-name DatabaseConnections --period 3600 --statistics Maximum",
    "aws logs start-query --log-group-name /ecs/orders-api --query-string 'stats count(*) by bin(1h)'",
    "aws logs get-query-results --query-id 1234",
    "aws logs tail /ecs/orders-api --since 15m",
    "aws ecs describe-services --cluster prod --services orders-api",
    "aws rds describe-db-instances --region eu-west-1",
    "aws s3 ls s3://example-bucket/",
    "aws secretsmanager describe-secret --secret-id orders/db",
    "aws ssm get-parameter --name /orders/pool-size",
    "aws ec2 wait instance-running --instance-ids i-0abc",
    "aws --version",
    # gcloud and gsutil reads
    "gcloud logging read 'severity>=ERROR' --freshness 1h --limit 50 --format json",
    "gcloud --project demo-proj monitoring dashboards list",
    "gcloud beta monitoring policies list",
    "gcloud run services list --region europe-west1",
    "gcloud run services describe orders-api --region europe-west1",
    "gcloud deploy releases list --delivery-pipeline web",
    "gcloud sql instances describe orders-db",
    "gcloud compute instances get-serial-port-output vm-1",
    "gcloud projects get-iam-policy demo-proj",
    "gcloud builds log 1234-abcd",
    "gcloud config get-value project",
    "gcloud auth list",
    "gcloud version",
    "gsutil ls gs://example-bucket",
    "gsutil -m du -s gs://example-bucket",
    # not governed at all
    "git status && git log --oneline -5",
    "grep -r 'kubectl delete' docs/",
    "echo 'never run kubectl delete here'",
    "which kubectl helm argocd",
    "cat <<'EOF' > notes.md\nkubectl delete pod x is what we did last time\nEOF\nls",
    "for p in $(kubectl get pods -o name); do kubectl describe $p; done",
    "if kubectl get ns web; then echo exists; fi",
    "find manifests -name '*.yaml' -exec kubectl diff -f {} \\;",
    "python3 -c 'print(1)'",
    "bash scripts/collect-facts.sh",
    "echo $((1 + 2))",
    # regressions: reads that the fixes below must not catch
    "kubectl config current-context",
    "helm template api ./charts/api -f values-staging.yaml",
    "helm show values ./charts/api",
    "docker exec toolbox k bash",          # `k` is kubectl only as the command word
    "kubectl get pods | awk '{print $1}'",
    "[ -x /usr/local/bin/kubectl ] && kubectl get pods",
    "ls manifests/*.yaml",
    "find . -name 'h*' -print",
    "source ./scripts/env.sh",
    "tmux ls",
]

DENY = [
    # kubectl writes, including flags before the verb
    "kubectl apply -f deploy.yaml",
    "kubectl -n payments delete pod api-7d9f",
    "kubectl --context prod patch deploy api -p '{}'",
    "kubectl edit cm api-config",
    "kubectl scale deploy/api --replicas=0",
    "kubectl rollout restart deploy/api",
    "kubectl rollout undo deploy/api",
    "kubectl drain node-1 --ignore-daemonsets",
    "kubectl cordon node-1",
    "kubectl exec -it api-7d9f -- sh",
    "kubectl cp api-7d9f:/tmp/dump ./dump",
    "kubectl create secret generic x --from-literal=a=b",
    "kubectl replace -f deploy.yaml",
    "kubectl annotate pod api-7d9f a=b",
    "kubectl label node node-1 role=db",
    "kubectl set image deploy/api api=example/api:2",
    "kubectl port-forward svc/db 5432",
    "kubectl config use-context prod",
    "kubectl config view --raw",
    "kubectl some-new-verb thing",  # unknown verb: allowlist, so denied
    # aliases, paths, wrappers
    "k delete pod x",
    "kubecolor delete pod x",
    "oc delete pod x",
    "/opt/homebrew/bin/kubectl delete pod x",
    "sudo kubectl delete pod x",
    "sudo -u ops kubectl delete pod x",
    "env KUBECONFIG=/tmp/k kubectl delete pod x",
    "env -S 'kubectl delete pod x'",
    "FOO=1 BAR=2 kubectl delete pod x",
    "nice -n 10 kubectl delete pod x",
    "nohup kubectl delete pod x &",
    "timeout 30 kubectl delete pod x",
    "command kubectl delete pod x",
    "microk8s kubectl delete pod x",
    "minikube kubectl -- delete pod x",
    # chaining and nesting
    "kubectl get pods && kubectl delete pod x",
    "kubectl get pods; kubectl delete pod x",
    "kubectl get pods || kubectl delete pod x",
    "kubectl get pods | kubectl delete -f -",
    "kubectl get pods\nkubectl delete pod x",
    "kubectl get pods # just looking\nkubectl delete pod x",
    "(kubectl delete pod x)",
    "echo $(kubectl delete pod x)",
    'echo "$(kubectl delete pod x)"',
    "echo `kubectl delete pod x`",
    "bash -c 'kubectl delete pod x'",
    "sh -lc \"kubectl get pods && kubectl delete pod x\"",
    "eval 'kubectl delete pod x'",
    "watch -n 5 kubectl delete pod x",
    "kubectl get pods -o name | xargs kubectl delete",
    "kubectl get pods -o name | xargs -I{} kubectl delete {}",
    "ssh bastion.example.internal 'kubectl delete pod x'",
    "for p in a b; do kubectl delete pod $p; done",
    "if true; then helm uninstall api; fi",
    "find . -name '*.yaml' -exec kubectl apply -f {} \\;",
    "docker exec toolbox kubectl delete pod x",
    "su -c 'kubectl delete pod x' ops",
    # helm writes
    "helm install api ./charts/api",
    "helm upgrade --install api ./charts/api",
    "helm -n web rollback api 3",
    "helm uninstall api",
    "helm delete api",
    "helm test api",
    "helm repo add example https://charts.example.com",
    # argocd writes
    "argocd app sync payments-api",
    "argocd app set payments-api --revision main",
    "argocd app delete payments-api",
    "argocd app rollback payments-api 12",
    "argocd app patch payments-api --patch '{}'",
    "argocd app actions run payments-api restart --kind Deployment",
    "argocd --server argocd.example.internal app sync payments-api",
    "argocd login argocd.example.internal",
    "argocd cluster add prod",
    # aws writes, and reads that print a secret
    "aws ecs update-service --cluster prod --service orders-api --desired-count 0",
    "aws --region eu-west-1 ecs update-service --cluster prod --service orders-api --force-new-deployment",
    "aws cloudwatch set-alarm-state --alarm-name orders-5xx --state-value OK --state-reason x",
    "aws cloudwatch put-metric-alarm --alarm-name x",
    "aws cloudwatch disable-alarm-actions --alarm-names orders-5xx",
    "aws rds reboot-db-instance --db-instance-identifier orders-db",
    "aws ec2 stop-instances --instance-ids i-0abc",
    "aws s3 rm s3://example-bucket/ --recursive",
    "aws s3 cp ./x s3://example-bucket/x",
    "aws lambda invoke --function-name f out.json",
    "aws sts assume-role --role-arn arn:aws:iam::111111111111:role/admin --role-session-name x",
    "aws ssm send-command --document-name AWS-RunShellScript",
    "aws eks update-kubeconfig --name prod",
    "aws secretsmanager get-secret-value --secret-id orders/db",
    "aws ecr get-login-password",
    "aws sts get-session-token",
    "aws ssm get-parameter --name /orders/db-password --with-decryption",
    "aws configure get aws_secret_access_key",
    "sudo aws ec2 terminate-instances --instance-ids i-0abc",
    "aws ecs list-services --cluster prod && aws ecs delete-service --service x",
    # gcloud and gsutil writes, and reads that print a secret
    "gcloud run deploy orders-api --image x",
    "gcloud run services update-traffic orders-api --to-revisions r1=100",
    "gcloud compute instances stop vm-1 --zone europe-west1-b",
    "gcloud compute instances delete list",
    "gcloud compute instances bulk-create --count 3 list",
    "gcloud sql instances restart orders-db",
    "gcloud sql instances patch orders-db --database-flags max_connections=500",
    "gcloud container clusters resize prod --num-nodes 0",
    "gcloud alpha monitoring policies delete projects/p/alertPolicies/1",
    "gcloud config set project other-proj",
    "gcloud auth print-access-token",
    "gcloud auth application-default print-access-token",
    "gcloud secrets versions access latest --secret orders-db",
    "gcloud container clusters get-credentials prod --region europe-west1",
    "gcloud config config-helper --format json",
    "gcloud init",
    "gsutil rm -r gs://example-bucket/logs",
    "gsutil -m cp -r ./x gs://example-bucket/",
    "bash -c 'gcloud run deploy orders-api --image x'",
    # fail closed
    "kubectl get pods 'unterminated",
    "KUBECTL=kubectl; $KUBECTL delete pod x",
    "${KUBECTL:-kubectl} delete pod x",
    "$KUBECTL delete pod x",
    "echo kubectl delete pod x | sh",
    'bash -c "$(echo kubectl delete pod x)"',
    'eval "$(printf kubectl) delete pod x"',
    "bash <<EOF\nkubectl delete pod x\nEOF",
    "python3 -c \"import os; os.system('kubectl delete pod x')\"",
    "perl -e 'system(\"helm uninstall api\")'",
]

# Bypasses a reviewer reproduced against an earlier version. Each list is also
# checked by its own test below, so a regression names the finding it reopens.
CONFIG_VIEW = [
    "kubectl config view --raw",
    "kubectl config view --raw=true",
    "kubectl config view --flatten",
    "kubectl config view --flatten=true --minify",
    "kubectl --context prod config view --raw",
    "kubectl config view",
    "k config view --raw",
]
EXPANDED_COMMAND_NAME = [
    "{kubectl,delete,pod,x}",
    "/usr/local/bin/kubec*l delete pod x",
    "kubec?l delete pod x",
    "kubec[t]l delete pod x",
    "ku{be,}ctl delete pod x",
    "/usr/bin/{kub,x}ectl get pods",        # could expand to kubectl; never named
    "/opt/{a..z}elm uninstall api",
    "sudo /usr/local/bin/hel? uninstall api",
    "/bin/ba?h -c 'kubectl delete pod x'",
    "setsid /usr/local/bin/kubec*l delete pod x",
    "find . -name '*.yaml' -exec kube*l apply -f {} \\;",
]
UNSEEN_SCRIPT = [
    "source <(echo kubectl delete pod x)",
    ". <(echo kubectl delete pod x)",
    "echo kubectl delete pod x | source /dev/stdin",
    "bash <(echo kubectl delete pod x)",
    "echo kubectl delete pod x | sh -s arg",
    "awk 'BEGIN { system(\"kubectl delete pod x\") }'",
    "gawk 'BEGIN { print \"helm uninstall api\" | \"sh\" }'",
    "tmux new-session -d 'kubectl delete pod x'",
    "tmux send-keys -t ops 'kub' Enter",
    "screen -dm kubectl delete pod x",
    "screen -S ops -X stuff 'k'",
    "nohup kubectl delete pod x &",
    "setsid kubectl delete pod x",
    "script -qc 'kubectl delete pod x' /dev/null",
    "echo 'kubectl delete pod x' | at now",
]
HELM_POST_RENDERER = [
    "helm template api ./charts/api --post-renderer ./render.sh",
    "helm template api ./charts/api --post-renderer=./render.sh",
    "helm lint ./charts/api --post-renderer ./render.sh",
    "helm show all ./charts/api --post-renderer ./render.sh",
    "helm diff upgrade api ./charts/api --post-renderer ./render.sh",
    "helm template api ./charts/api --post-renderer-args=--fix",
]


def run_hook(payload: str):
    return subprocess.run(
        [sys.executable, HOOK], input=payload, capture_output=True, text=True, timeout=10
    )


def bash_payload(command: str) -> str:
    return json.dumps({
        "session_id": "test",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command, "description": "test"},
        "tool_use_id": "toolu_test",
    })


class TestDecisions(unittest.TestCase):
    def test_allow(self):
        for cmd in ALLOW:
            with self.subTest(cmd=cmd):
                self.assertIsNone(hook.analyse(cmd), f"should be allowed: {cmd!r}")

    def test_deny(self):
        for cmd in DENY:
            with self.subTest(cmd=cmd):
                self.assertIsNotNone(hook.analyse(cmd), f"should be denied: {cmd!r}")

    def test_case_counts(self):
        self.assertGreaterEqual(len(ALLOW) + len(DENY), 25)


class TestReviewedBypasses(unittest.TestCase):
    def assert_all_denied(self, cases, must_mention):
        for cmd in cases:
            with self.subTest(cmd=cmd):
                reason = hook.analyse(cmd)
                self.assertIsNotNone(reason, f"should be denied: {cmd!r}")
                self.assertIn(must_mention, reason)

    def test_kubectl_config_view_is_denied_in_every_spelling(self):
        self.assert_all_denied(CONFIG_VIEW, "config view")
        self.assertIn("current-context", hook.analyse("kubectl config view --raw=true"))

    def test_command_name_built_by_brace_expansion_or_glob(self):
        self.assert_all_denied(EXPANDED_COMMAND_NAME, "")

    def test_scripts_the_hook_cannot_see_fail_closed(self):
        self.assert_all_denied(UNSEEN_SCRIPT, "")

    def test_helm_post_renderer_is_denied_on_every_verb(self):
        self.assert_all_denied(HELM_POST_RENDERER, "--post-renderer")

    def test_k_is_kubectl_only_as_the_command_word(self):
        self.assertIsNone(hook.analyse("docker exec toolbox k bash"))
        self.assertIsNotNone(hook.analyse("k delete pod x"))
        self.assertIsNotNone(hook.analyse("docker exec toolbox kubectl delete pod x"))


class TestEndToEnd(unittest.TestCase):
    """Drive the script exactly as Claude Code does: JSON on stdin, exit code out."""

    def test_read_exits_0_silently(self):
        r = run_hook(bash_payload("kubectl get pods -n web"))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")

    def test_write_exits_2_with_reason_on_stderr(self):
        r = run_hook(bash_payload("kubectl -n web rollout restart deploy/api"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("rollout restart", r.stderr)
        self.assertIn("merge request", r.stderr)

    def test_other_tools_pass_through(self):
        payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}})
        self.assertEqual(run_hook(payload).returncode, 0)

    def test_bad_json_mentioning_kubectl_fails_closed(self):
        self.assertEqual(run_hook('{"tool_name": "Bash", "command": "kubectl delete').returncode, 2)

    def test_bad_json_not_mentioning_governed_binaries_passes(self):
        self.assertEqual(run_hook("not json at all").returncode, 0)

    def test_missing_command_mentioning_kubectl_fails_closed(self):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"cmd": "kubectl delete pod x"}})
        self.assertEqual(run_hook(payload).returncode, 2)


if __name__ == "__main__":
    unittest.main()
