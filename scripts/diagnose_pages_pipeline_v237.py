#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API = "https://api.github.com"
LIVE_DEPLOYMENT = "https://khaledaltheeb.github.io/pterminology-site/deployment.json"
WORKFLOWS = {
    "build": "validate-all-labs-v22.yml",
    "discovery": "audit-production-discovery-v220.yml",
    "deploy": "deploy-validated-main.yml",
    "proof": "verify-special-needs-live-v236.yml",
}
EXPECTED_ARTIFACTS = {
    "build": "validated-production-site",
    "discovery": "validated-production-site",
    "deploy": None,
    "proof": "special-needs-live-v236",
}


class DiagnosticError(RuntimeError):
    pass


def api_get(repository: str, token: str, path: str) -> Any:
    request = urllib.request.Request(
        f"{API}/repos/{repository}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pterminology-pages-diagnostic-v237",
        },
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))


def public_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{url}?diagnostic={int(time.time())}",
        headers={
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "pterminology-pages-diagnostic-v237",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    return data if isinstance(data, dict) else {"error": "live deployment response is not an object"}


def compact_run(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": run.get("id"),
        "run_number": run.get("run_number"),
        "run_attempt": run.get("run_attempt"),
        "event": run.get("event"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "head_branch": run.get("head_branch"),
        "head_sha": run.get("head_sha"),
        "created_at": run.get("created_at"),
        "updated_at": run.get("updated_at"),
        "html_url": run.get("html_url"),
        "display_title": run.get("display_title"),
    }


def select_run(runs: list[dict[str, Any]], target_sha: str, event: str) -> dict[str, Any] | None:
    exact = [run for run in runs if run.get("head_sha") == target_sha and run.get("event") == event]
    if exact:
        return exact[0]
    same_event = [run for run in runs if run.get("event") == event]
    return same_event[0] if same_event else (runs[0] if runs else None)


def run_evidence(repository: str, token: str, run: dict[str, Any] | None) -> dict[str, Any]:
    if run is None:
        return {"run": None, "jobs": [], "artifacts": []}
    run_id = run["id"]
    jobs_payload = api_get(repository, token, f"/actions/runs/{run_id}/jobs?per_page=100")
    artifacts_payload = api_get(repository, token, f"/actions/runs/{run_id}/artifacts?per_page=100")
    jobs = []
    for job in jobs_payload.get("jobs", []):
        steps = [
            {
                "name": step.get("name"),
                "status": step.get("status"),
                "conclusion": step.get("conclusion"),
                "number": step.get("number"),
            }
            for step in job.get("steps", [])
        ]
        jobs.append(
            {
                "id": job.get("id"),
                "name": job.get("name"),
                "status": job.get("status"),
                "conclusion": job.get("conclusion"),
                "started_at": job.get("started_at"),
                "completed_at": job.get("completed_at"),
                "html_url": job.get("html_url"),
                "steps": steps,
            }
        )
    artifacts = [
        {
            "id": artifact.get("id"),
            "name": artifact.get("name"),
            "expired": artifact.get("expired"),
            "size_in_bytes": artifact.get("size_in_bytes"),
            "created_at": artifact.get("created_at"),
            "updated_at": artifact.get("updated_at"),
        }
        for artifact in artifacts_payload.get("artifacts", [])
    ]
    return {"run": compact_run(run), "jobs": jobs, "artifacts": artifacts}


def first_failed_step(evidence: dict[str, Any]) -> dict[str, Any] | None:
    for job in evidence.get("jobs", []):
        if job.get("conclusion") not in {None, "success", "skipped"}:
            for step in job.get("steps", []):
                if step.get("conclusion") == "failure":
                    return {"job": job.get("name"), "step": step.get("name"), "job_url": job.get("html_url")}
            return {"job": job.get("name"), "step": None, "job_url": job.get("html_url")}
    return None


def workflow_runs(repository: str, token: str, workflow: str) -> list[dict[str, Any]]:
    encoded = urllib.parse.quote(workflow, safe="")
    payload = api_get(repository, token, f"/actions/workflows/{encoded}/runs?branch=main&per_page=30")
    return payload.get("workflow_runs", [])


def diagnose(output: Path) -> tuple[dict[str, Any], int]:
    repository = os.environ.get("GITHUB_REPOSITORY", "khaledaltheeb/pterminology-site")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise DiagnosticError("GH_TOKEN or GITHUB_TOKEN is required")

    main_ref = api_get(repository, token, "/git/ref/heads/main")
    target_sha = main_ref["object"]["sha"]
    target_commit = api_get(repository, token, f"/commits/{target_sha}")

    stages: dict[str, Any] = {}
    recent: dict[str, list[dict[str, Any]]] = {}
    expected_events = {"build": "push", "discovery": "workflow_run", "deploy": "workflow_run", "proof": "workflow_run"}

    for stage, workflow in WORKFLOWS.items():
        runs = workflow_runs(repository, token, workflow)
        recent[stage] = [compact_run(run) for run in runs[:10]]
        selected = select_run(runs, target_sha, expected_events[stage])
        evidence = run_evidence(repository, token, selected)
        evidence["workflow_file"] = workflow
        evidence["selected_exact_target_sha"] = bool(selected and selected.get("head_sha") == target_sha)
        evidence["first_failed_step"] = first_failed_step(evidence)
        expected_artifact = EXPECTED_ARTIFACTS[stage]
        evidence["expected_artifact"] = expected_artifact
        evidence["expected_artifact_present"] = (
            True
            if expected_artifact is None
            else any(item.get("name") == expected_artifact and not item.get("expired") for item in evidence["artifacts"])
        )
        stages[stage] = evidence

    live = public_json(LIVE_DEPLOYMENT)
    live_sha = live.get("commit")

    blocking_stage = None
    blocking_reason = None
    exit_code = 0

    build = stages["build"]
    if not build["selected_exact_target_sha"]:
        blocking_stage, blocking_reason, exit_code = "build", "No main push run was found for the current main SHA", 10
    elif build["run"].get("status") != "completed":
        blocking_stage, blocking_reason, exit_code = "build", "The current main production build is not completed", 11
    elif build["run"].get("conclusion") != "success":
        blocking_stage, blocking_reason, exit_code = "build", "The current main production build did not succeed", 12
    elif not build["expected_artifact_present"]:
        blocking_stage, blocking_reason, exit_code = "build", "The successful main build did not retain validated-production-site", 13
    else:
        discovery = stages["discovery"]
        if not discovery["selected_exact_target_sha"]:
            blocking_stage, blocking_reason, exit_code = "discovery", "No discovery workflow_run was found for the current main SHA", 20
        elif discovery["run"].get("status") != "completed":
            blocking_stage, blocking_reason, exit_code = "discovery", "The discovery audit is not completed", 21
        elif discovery["run"].get("conclusion") != "success":
            blocking_stage, blocking_reason, exit_code = "discovery", "The discovery audit failed", 22
        elif not discovery["expected_artifact_present"]:
            blocking_stage, blocking_reason, exit_code = "discovery", "The discovery audit did not retain the republished production artifact", 23
        else:
            deploy = stages["deploy"]
            if not deploy["selected_exact_target_sha"]:
                blocking_stage, blocking_reason, exit_code = "deploy", "No Pages deployment workflow_run was found for the current main SHA", 30
            elif deploy["run"].get("status") != "completed":
                blocking_stage, blocking_reason, exit_code = "deploy", "The Pages deployment is not completed", 31
            elif deploy["run"].get("conclusion") != "success":
                blocking_stage, blocking_reason, exit_code = "deploy", "The Pages deployment failed", 32
            elif live_sha != target_sha:
                blocking_stage, blocking_reason, exit_code = "live", "Pages completed but the public deployment stamp does not match current main", 40
            else:
                proof = stages["proof"]
                if not proof["selected_exact_target_sha"]:
                    blocking_stage, blocking_reason, exit_code = "proof", "Pages is current but the authoritative special-needs proof run is absent", 50
                elif proof["run"].get("status") != "completed":
                    blocking_stage, blocking_reason, exit_code = "proof", "The authoritative live proof is not completed", 51
                elif proof["run"].get("conclusion") != "success":
                    blocking_stage, blocking_reason, exit_code = "proof", "The authoritative live proof failed", 52

    report = {
        "version": 237,
        "status": "passed" if exit_code == 0 else "blocked",
        "repository": repository,
        "target_main": {
            "sha": target_sha,
            "message": target_commit.get("commit", {}).get("message"),
            "date": target_commit.get("commit", {}).get("committer", {}).get("date"),
            "html_url": target_commit.get("html_url"),
        },
        "live_deployment": {
            "sha": live_sha,
            "schema_version": live.get("schema_version"),
            "validated_at": live.get("validated_at"),
            "workflow_run": live.get("workflow_run"),
            "raw_error": live.get("error"),
            "matches_main": live_sha == target_sha,
        },
        "blocking_stage": blocking_stage,
        "blocking_reason": blocking_reason,
        "exit_code": exit_code,
        "stages": stages,
        "recent_runs": recent,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report, exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("pages-pipeline-diagnostic-v237.json"))
    args = parser.parse_args()
    report, exit_code = diagnose(args.output.resolve())
    print(json.dumps({
        "version": report["version"],
        "status": report["status"],
        "target_sha": report["target_main"]["sha"],
        "live_sha": report["live_deployment"]["sha"],
        "blocking_stage": report["blocking_stage"],
        "blocking_reason": report["blocking_reason"],
        "exit_code": report["exit_code"],
    }, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
