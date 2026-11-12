"""Tests for the m64 pipeline scripts. No network: a stub argocd CLI and a local mock GitLab API.

Run from the kit root:  python3 -m pytest 04-pipeline/tests
Needs: bash, curl, jq (and shellcheck for the lint test, skipped if absent).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pytest

KIT = Path(__file__).resolve().parents[2]
PIPELINE = KIT / "04-pipeline"
DRIFT = PIPELINE / "argo-drift-check.sh"
COLLECT = PIPELINE / "scripts" / "collect-failed-job-logs.sh"
POST = PIPELINE / "scripts" / "post-mr-note.sh"
REDACT = PIPELINE / "scripts" / "redact.sh"
SAMPLE_LOG = KIT / "sample-data" / "failed-job.log"
SCRIPTS = [DRIFT, COLLECT, POST, REDACT]

pytestmark = pytest.mark.skipif(not (shutil.which("jq") and shutil.which("curl")), reason="needs jq and curl")


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_bash_syntax(script: Path):
    subprocess.run(["bash", "-n", str(script)], check=True)


@pytest.mark.skipif(not shutil.which("shellcheck"), reason="shellcheck not installed")
@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_shellcheck_clean(script: Path):
    result = subprocess.run(["shellcheck", "-x", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


# --- argo-drift-check.sh -----------------------------------------------------

STUB_ARGOCD = r"""#!/usr/bin/env bash
echo "$*" >> "$ARGOCD_STUB_LOG"
case "$1 $2" in
  "app list") cat "$ARGOCD_STUB_DIR/apps.json" ;;
  "app diff")
    app="$3"
    if [ -f "$ARGOCD_STUB_DIR/$app.diff" ]; then cat "$ARGOCD_STUB_DIR/$app.diff"; exit 1; fi
    if [ -f "$ARGOCD_STUB_DIR/$app.err" ]; then cat "$ARGOCD_STUB_DIR/$app.err" >&2; exit 20; fi
    exit 0 ;;
  *) echo "stub: unexpected verb $*" >&2; exit 99 ;;
esac
"""


def app(name: str, sync: str = "Synced", health: str = "Healthy") -> dict:
    return {"metadata": {"name": name}, "status": {"sync": {"status": sync}, "health": {"status": health}}}


@pytest.fixture
def argo(tmp_path: Path):
    stub_bin = tmp_path / "stubbin"
    stub_bin.mkdir()
    (stub_bin / "argocd").write_text(STUB_ARGOCD)
    (stub_bin / "argocd").chmod(0o755)
    data = tmp_path / "data"
    data.mkdir()
    log = tmp_path / "calls.log"
    log.touch()

    def run(apps: list[dict], *args: str, diffs: dict[str, str] | None = None, errs: dict[str, str] | None = None, env_extra=None):
        (data / "apps.json").write_text(json.dumps(apps))
        for name, text in (diffs or {}).items():
            (data / f"{name}.diff").write_text(text)
        for name, text in (errs or {}).items():
            (data / f"{name}.err").write_text(text)
        env = {
            **os.environ,
            "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}",
            "ARGOCD_SERVER": "argocd.example.internal",
            "ARGOCD_AUTH_TOKEN": "fake-token-not-real",
            "ARGOCD_STUB_DIR": str(data),
            "ARGOCD_STUB_LOG": str(log),
            **(env_extra or {}),
        }
        result = subprocess.run(["bash", str(DRIFT), *args], capture_output=True, text=True, env=env)
        return result, log.read_text().splitlines()

    return run


def test_drift_clean(argo):
    result, calls = argo([app("orders-api-prod"), app("payments-api-prod")])
    assert result.returncode == 0, result.stderr
    assert "| orders-api-prod | Synced | Healthy | no |" in result.stdout
    assert "Drifted or out of sync: 0" in result.stdout


def test_drift_found_and_truncated(argo):
    diff = "\n".join(f"line {i}" for i in range(100)) + "\n"
    result, _ = argo([app("orders-api-prod", sync="OutOfSync"), app("ok")], "-n", "5", diffs={"orders-api-prod": diff})
    assert result.returncode == 1
    assert "| orders-api-prod | OutOfSync | Healthy | yes |" in result.stdout
    assert "line 4" in result.stdout and "line 5\n" not in result.stdout
    assert "95 more lines" in result.stdout


def test_out_of_sync_without_diff_still_counts(argo):
    result, _ = argo([app("orders-api-prod", sync="OutOfSync")])
    assert result.returncode == 1
    assert "Drifted or out of sync: 1" in result.stdout


def test_diff_error_exits_2(argo):
    result, _ = argo([app("broken")], errs={"broken": "rpc error: permission denied"})
    assert result.returncode == 2
    assert "diff failed" in result.stdout and "permission denied" in result.stdout


def test_only_read_only_verbs_are_called(argo):
    argo([app("a", sync="OutOfSync"), app("b")], "-p", "orders", "-l", "team=orders", diffs={"a": "x\n"})
    _, calls = argo([app("a")])
    verbs = {" ".join(call.split()[:2]) for call in calls}
    assert verbs <= {"app list", "app diff", "app get"}, verbs
    assert all("--server argocd.example.internal" in call for call in calls)
    assert not any("fake-token" in call for call in calls), "token must come from the environment, not argv"
    assert any("-p orders" in call and "-l team=orders" in call for call in calls if call.startswith("app list"))


def test_refuse_guard_blocks_mutating_verbs(tmp_path: Path):
    # Source the script's guard function in isolation and try a sync.
    script = DRIFT.read_text()
    start = script.index("argocd_ro() {")
    end = script.index("\n}\n", start) + 3
    harness = tmp_path / "guard.sh"
    harness.write_text("global_flags=()\nargocd() { echo CALLED; }\n" + script[start:end] + 'argocd_ro app sync orders-api-prod\n')
    result = subprocess.run(["bash", str(harness)], capture_output=True, text=True)
    assert result.returncode == 2
    assert "CALLED" not in result.stdout
    assert "refused" in result.stderr


def test_report_file_and_missing_env(argo, tmp_path: Path):
    out = tmp_path / "report.md"
    result, _ = argo([app("a")], "-o", str(out))
    assert result.returncode == 0 and out.read_text().startswith("# Argo CD drift report")
    result, _ = argo([app("a")], env_extra={"ARGOCD_AUTH_TOKEN": "", "ARGOCD_API_TOKEN": ""})
    assert result.returncode != 0 and "ARGOCD_AUTH_TOKEN" in result.stderr


def test_drift_accepts_the_mcp_token_name(argo):
    # 01-access/ names the read-only token ARGOCD_API_TOKEN (what argocd-mcp reads);
    # the script hands it to the CLI as ARGOCD_AUTH_TOKEN, never on argv.
    result, calls = argo([app("a")], env_extra={"ARGOCD_AUTH_TOKEN": "", "ARGOCD_API_TOKEN": "mcp-token-not-real"})
    assert result.returncode == 0, result.stderr
    assert not any("mcp-token" in call for call in calls)


# --- collect-failed-job-logs.sh and post-mr-note.sh ---------------------------

class MockGitLab(BaseHTTPRequestHandler):
    jobs: list = []
    traces: dict = {}
    notes: list = []
    seen_tokens: list = []

    def log_message(self, *args):  # keep test output quiet
        pass

    def _send(self, code: int, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.seen_tokens.append(self.headers.get("PRIVATE-TOKEN"))
        url = urlparse(self.path)
        if url.path == "/api/v4/projects/1142/pipelines/77/jobs":
            assert parse_qs(url.query).get("scope[]") == ["failed"]
            return self._send(200, json.dumps(self.jobs).encode())
        if url.path.startswith("/api/v4/projects/1142/jobs/") and url.path.endswith("/trace"):
            job_id = int(url.path.split("/")[-2])
            return self._send(200, self.traces[job_id].encode(), "text/plain")
        self._send(404, b"{}")

    def do_POST(self):
        self.seen_tokens.append(self.headers.get("PRIVATE-TOKEN"))
        length = int(self.headers["Content-Length"])
        form = parse_qs(self.rfile.read(length).decode())
        self.notes.append({"path": unquote(self.path), "body": form["body"][0]})
        self._send(201, b'{"id": 1}')


@pytest.fixture
def gitlab():
    MockGitLab.jobs, MockGitLab.traces, MockGitLab.notes, MockGitLab.seen_tokens = [], {}, [], []
    server = ThreadingHTTPServer(("127.0.0.1", 0), MockGitLab)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = {
        **os.environ,
        "CI_API_V4_URL": f"http://127.0.0.1:{server.server_address[1]}/api/v4",
        "CI_PROJECT_ID": "1142",
        "CI_PIPELINE_ID": "77",
        "CI_PIPELINE_URL": "https://gitlab.example.internal/orders/orders-api/-/pipelines/77",
        "DIAGNOSE_API_TOKEN": "fake-diagnose-token",
    }
    yield MockGitLab, env
    server.shutdown()


def test_collect_strips_redacts_and_tails(gitlab, tmp_path: Path):
    mock, env = gitlab
    esc = "\x1b"
    trace = (
        f"section_start:1700000000:step_script\r{esc}[0K{esc}[32;1mExecuting step{esc}[0;m\n"
        "export DB_PASSWORD=hunter2-not-real\n"
        "Authorization: Bearer abc.def.ghi-not-real\n"
        "token glpat-AAAAAAAAAAAAAAAAAAAAAAAA leaked\n"
        "-----BEGIN RSA PRIVATE KEY-----\nMIIfake\n-----END RSA PRIVATE KEY-----\n"
        + SAMPLE_LOG.read_text()
    )
    mock.jobs = [
        {"id": 9001, "name": "integration-test", "stage": "test", "failure_reason": "script_failure", "web_url": "https://gitlab.example.internal/j/9001"},
        {"id": 9002, "name": "lint: helm", "stage": "lint", "failure_reason": None, "web_url": "https://gitlab.example.internal/j/9002"},
    ]
    mock.traces = {9001: trace, 9002: "only line\n"}
    out = tmp_path / "diagnose"
    result = subprocess.run(["bash", str(COLLECT), str(out)], capture_output=True, text=True, env={**env, "DIAGNOSE_TAIL_LINES": "1000"})
    assert result.returncode == 0, result.stderr
    log = (out / "integration-test-9001.log").read_text()
    assert esc not in log and "section_start" not in log and "\r" not in log
    assert "hunter2" not in log and "abc.def.ghi" not in log and "glpat-AAAA" not in log and "MIIfake" not in log
    assert "[REDACTED PRIVATE KEY]" in log
    assert "Apparent connection leak detected" in log  # the evidence survives
    assert (out / "lint__helm-9002.log").exists()
    index = (out / "failed-jobs.md").read_text()
    assert "| integration-test | test | script_failure |" in index and "| lint: helm | lint | unknown |" in index
    assert set(mock.seen_tokens) == {"fake-diagnose-token"}


def test_collect_tail_and_max_jobs(gitlab, tmp_path: Path):
    mock, env = gitlab
    mock.jobs = [{"id": i, "name": f"job{i}", "stage": "test"} for i in (1, 2, 3)]
    mock.traces = {i: "".join(f"{i}-{n}\n" for n in range(50)) for i in (1, 2, 3)}
    out = tmp_path / "d"
    subprocess.run(["bash", str(COLLECT), str(out)], check=True, capture_output=True, env={**env, "DIAGNOSE_TAIL_LINES": "5", "DIAGNOSE_MAX_JOBS": "2"})
    assert (out / "job1-1.log").read_text().splitlines() == [f"1-{n}" for n in range(45, 50)]
    assert not (out / "job3-3.log").exists()


def test_collect_no_failed_jobs(gitlab, tmp_path: Path):
    _, env = gitlab
    out = tmp_path / "d"
    subprocess.run(["bash", str(COLLECT), str(out)], check=True, capture_output=True, env=env)
    assert "No failed jobs found." in (out / "failed-jobs.md").read_text()


def test_post_note_to_mr(gitlab, tmp_path: Path):
    mock, env = gitlab
    diagnosis = tmp_path / "diagnosis.md"
    diagnosis.write_text("### integration-test — code-or-test\nleak at OrderExportService.java:88 & more\n")
    result = subprocess.run(["bash", str(POST), str(diagnosis)], capture_output=True, text=True, env={**env, "CI_MERGE_REQUEST_IID": "517"})
    assert result.returncode == 0, result.stderr
    (note,) = mock.notes
    assert note["path"] == "/api/v4/projects/1142/merge_requests/517/notes"
    assert note["body"].startswith("**Automated diagnosis")
    assert "OrderExportService.java:88 & more" in note["body"]
    assert "It changed nothing" in note["body"]


def test_post_note_truncates(gitlab, tmp_path: Path):
    mock, env = gitlab
    diagnosis = tmp_path / "diagnosis.md"
    diagnosis.write_text("x" * 500)
    subprocess.run(["bash", str(POST), str(diagnosis)], check=True, capture_output=True, env={**env, "CI_MERGE_REQUEST_IID": "1", "DIAGNOSE_NOTE_MAX_BYTES": "100"})
    assert "truncated" in mock.notes[0]["body"] and "x" * 101 not in mock.notes[0]["body"]


def test_post_note_skips_outside_mr_and_rejects_empty(gitlab, tmp_path: Path):
    mock, env = gitlab
    diagnosis = tmp_path / "diagnosis.md"
    diagnosis.write_text("something")
    env.pop("CI_MERGE_REQUEST_IID", None)
    result = subprocess.run(["bash", str(POST), str(diagnosis)], capture_output=True, text=True, env=env)
    assert result.returncode == 0 and "Not a merge request pipeline" in result.stdout and mock.notes == []
    empty = tmp_path / "empty.md"
    empty.write_text("")
    result = subprocess.run(["bash", str(POST), str(empty)], capture_output=True, text=True, env={**env, "CI_MERGE_REQUEST_IID": "1"})
    assert result.returncode == 1 and mock.notes == []


def test_post_note_redacts_the_outgoing_diagnosis(gitlab, tmp_path: Path):
    # The agent read logs an MR author controls; whatever it echoes is scrubbed
    # on the way out with the same pass as the logs on the way in.
    mock, env = gitlab
    model_key = "sk-ant-api03-" + "Q" * 40
    job_token = "glcbt-64_" + "J" * 24
    diagnosis = tmp_path / "diagnosis.md"
    diagnosis.write_text(
        "### integration-test — code-or-test\n"
        f"The log printed ANTHROPIC_API_KEY={model_key}\n"
        f"remote: https://gitlab-ci-token:{job_token}@gitlab.example.internal/orders/orders-api.git\n"
        "Personal token glpat-ZZZZZZZZZZZZZZZZZZZZZZZZ in a curl line\n"
        "Authorization: Bearer eyJhbGciOi.not-real.sig\n"
        "export DB_PASSWORD=hunter2-not-real\n"
        "Literal value of the job's own token: fake-diagnose-token\n"
        "plain-job-token-value-not-real appears here\n"
        "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAA\n-----END OPENSSH PRIVATE KEY-----\n"
        "leak at OrderExportService.java:88\n"
    )
    result = subprocess.run(
        ["bash", str(POST), str(diagnosis)], capture_output=True, text=True,
        env={**env, "CI_MERGE_REQUEST_IID": "517", "CI_JOB_TOKEN": "plain-job-token-value-not-real"},
    )
    assert result.returncode == 0, result.stderr
    body = mock.notes[0]["body"]
    for secret in (model_key, job_token, "glpat-ZZZZ", "eyJhbGciOi", "hunter2", "fake-diagnose-token",
                   "plain-job-token-value-not-real", "b3BlbnNzaC1rZXk"):
        assert secret not in body, secret
    assert "https://[REDACTED]@gitlab.example.internal/orders/orders-api.git" in body
    assert "[REDACTED PRIVATE KEY]" in body
    assert "OrderExportService.java:88" in body  # the evidence survives


def test_post_note_redacts_before_truncating(gitlab, tmp_path: Path):
    # A cut must not leave the head of a secret that the patterns would only
    # recognise whole.
    mock, env = gitlab
    diagnosis = tmp_path / "diagnosis.md"
    diagnosis.write_text("x" * 90 + "glpat-" + "A" * 30 + "\n")
    subprocess.run(["bash", str(POST), str(diagnosis)], check=True, capture_output=True,
                   env={**env, "CI_MERGE_REQUEST_IID": "1", "DIAGNOSE_NOTE_MAX_BYTES": "100"})
    body = mock.notes[0]["body"]
    assert "glpat-" not in body and "AAAA" not in body


def test_post_note_redacts_extra_named_variables(gitlab, tmp_path: Path):
    mock, env = gitlab
    diagnosis = tmp_path / "diagnosis.md"
    diagnosis.write_text("the vault said s3cr3t-value-not-real and stopped\n")
    subprocess.run(["bash", str(POST), str(diagnosis)], check=True, capture_output=True,
                   env={**env, "CI_MERGE_REQUEST_IID": "1", "VAULT_THING": "s3cr3t-value-not-real",
                        "DIAGNOSE_REDACT_VARS": "VAULT_THING", "SHORT_ONE": "abc"})
    body = mock.notes[0]["body"]
    assert "s3cr3t-value-not-real" not in body and "the vault said [REDACTED] and stopped" in body


def _claude_argv(script: str) -> list[str]:
    import shlex
    line = next(cmd for cmd in script.split("\n") if cmd.startswith("claude "))
    argv = shlex.split(line)
    return argv[:argv.index(">")] if ">" in argv else argv


def _flag(argv: list[str], name: str) -> str:
    assert argv.count(name) == 1, f"{name} must appear exactly once"
    return argv[argv.index(name) + 1]


def test_ci_snippet_shape():
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load((PIPELINE / "gitlab-ci.diagnose.yml").read_text())
    job = doc["diagnose-failed-job"]
    assert job["stage"] == ".post" and job["allow_failure"] is True
    assert "environment" not in job
    assert any(rule.get("when") == "on_failure" and "merge_request_event" in rule["if"] for rule in job["rules"])
    script = "\n".join(job["script"])
    argv = _claude_argv(script)
    assert argv[:2] == ["claude", "--bare"] and argv[2] == "-p"
    assert _flag(argv, "--permission-mode") == "dontAsk"
    assert _flag(argv, "--tools") == "Read,Grep,Glob"
    denied = _flag(argv, "--disallowedTools").split(",")
    assert {"Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch"} <= set(denied)
    for path in ("04-pipeline/scripts/collect-failed-job-logs.sh", "04-pipeline/scripts/post-mr-note.sh", "04-pipeline/prompts/diagnose-failed-job.md"):
        assert path in script and (KIT / path).exists()


def test_ci_agent_reads_are_scoped_to_the_checkout():
    # Regression: a bare "Read,Grep,Glob" allow pre-approved reads anywhere on the
    # runner (/proc/self/environ, .git/config with the job token, $HOME), while the
    # input is attacker-influenced MR pipeline logs.
    yaml = pytest.importorskip("yaml")
    job = yaml.safe_load((PIPELINE / "gitlab-ci.diagnose.yml").read_text())["diagnose-failed-job"]
    argv = _claude_argv("\n".join(job["script"]))
    allowed = _flag(argv, "--allowedTools").split(",")
    assert allowed and all(rule.startswith("Read(./") and rule.endswith(")") for rule in allowed), allowed
    assert not {"Read", "Grep", "Glob"} & set(allowed), "a bare tool name pre-approves every path"
    denied = set(_flag(argv, "--disallowedTools").split(","))
    for rule in ("Read(.git/**)", "Read(//proc/**)", "Read(//etc/**)", "Read(~/**)", "Read(//root/**)",
                 "Read(//tmp/**)", "Read(.env)", "Read(*.env)", "Read(.git-credentials)", "Read(.netrc)"):
        assert rule in denied, rule
    settings = json.loads(_flag(argv, "--settings"))
    assert settings["permissions"]["blockReadsOutsideWorkingDirectories"] is True
    # The diagnosis is redacted on the way out by the script that posts it.
    post = POST.read_text()
    assert "redact.sh" in post and 'redact <"$diagnosis"' in post
