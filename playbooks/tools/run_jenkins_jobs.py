#!/usr/bin/env python3
"""Trigger and monitor Jenkins jobs defined in a YAML config file."""

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import yaml


def load_yaml(path):
    if path == "-":
        return yaml.safe_load(sys.stdin)
    with open(path) as f:
        return yaml.safe_load(f)


def make_session(config):
    jenkins = config["jenkins"]
    token = jenkins.get("token") or os.environ.get("JENKINS_API_TOKEN", "")
    if not token:
        sys.exit("Error: Jenkins API token not set in config or JENKINS_API_TOKEN env var")

    session = requests.Session()
    session.auth = (jenkins["user"], token)
    session.headers["Content-Type"] = "application/json"
    return session


def get_crumb(session, base_url):
    """Fetch CSRF crumb if Jenkins requires it."""
    try:
        resp = session.get(f"{base_url}/crumbIssuer/api/json", timeout=10)
        if resp.ok:
            data = resp.json()
            return {data["crumbRequestField"]: data["crumb"]}
    except Exception:
        pass
    return {}


def trigger_job(session, base_url, job_name, parameters, crumb):
    """Trigger a Jenkins job and return the queue item URL."""
    job_url = f"{base_url}/job/{'/job/'.join(job_name.split('/'))}"

    if parameters:
        url = f"{job_url}/buildWithParameters"
        resp = session.post(url, params=parameters, headers=crumb, timeout=30)
    else:
        url = f"{job_url}/build"
        resp = session.post(url, headers=crumb, timeout=30)

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to trigger '{job_name}': HTTP {resp.status_code} - {resp.text}")

    queue_url = resp.headers.get("Location")
    if queue_url:
        return queue_url.rstrip("/") + "/api/json"
    return None


def wait_for_build_start(session, queue_url, timeout):
    """Poll the queue item until Jenkins assigns a build number."""
    deadline = time.time() + timeout if timeout else None
    while True:
        if deadline and time.time() > deadline:
            raise TimeoutError("Timed out waiting for build to start")
        try:
            resp = session.get(queue_url, timeout=10)
            if resp.ok:
                data = resp.json()
                executable = data.get("executable")
                if executable:
                    return executable["url"]
                if data.get("cancelled"):
                    raise RuntimeError("Build was cancelled in queue")
        except (requests.RequestException, KeyError):
            pass
        time.sleep(3)


def wait_for_build_finish(session, build_url, timeout):
    """Poll the build until it completes. Returns the build result."""
    api_url = build_url.rstrip("/") + "/api/json"
    deadline = time.time() + timeout if timeout else None
    while True:
        if deadline and time.time() > deadline:
            raise TimeoutError("Timed out waiting for build to finish")
        try:
            resp = session.get(api_url, timeout=10)
            if resp.ok:
                data = resp.json()
                if not data.get("building", True):
                    return data.get("result", "UNKNOWN"), data.get("url", build_url)
        except requests.RequestException:
            pass
        time.sleep(5)


def run_job(session, base_url, job, crumb, timeout):
    """Trigger a job, wait for completion, return (name, result, url)."""
    name = job["name"]
    params = job.get("parameters")
    print(f"  Triggering: {name}")

    queue_url = trigger_job(session, base_url, name, params, crumb)
    if not queue_url:
        return name, "TRIGGERED (no queue URL)", ""

    build_url = wait_for_build_start(session, queue_url, timeout)
    print(f"  Started:    {name} -> {build_url}")

    result, url = wait_for_build_finish(session, build_url, timeout)
    status = "OK" if result == "SUCCESS" else "FAIL"
    print(f"  Finished:   {name} -> {result} ({status})")
    return name, result, url


def run_sequential(session, base_url, jobs, crumb, timeout, fail_fast):
    results = []
    for job in jobs:
        name, result, url = run_job(session, base_url, job, crumb, timeout)
        results.append((name, result, url))
        if fail_fast and result != "SUCCESS":
            print(f"\n  Stopping early: '{name}' did not succeed ({result})")
            break
    return results


def run_parallel(session, base_url, jobs, crumb, timeout):
    results = []
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {
            pool.submit(run_job, session, base_url, job, crumb, timeout): job["name"]
            for job in jobs
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                results.append((futures[future], f"ERROR: {e}", ""))
    return results


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_jenkins = os.path.join(script_dir, "config.yaml")

    parser = argparse.ArgumentParser(description="Run Jenkins jobs from a YAML config")
    parser.add_argument("-c", "--config", default="jenkins_jobs.yaml",
                        help="Jobs config file (or '-' for stdin)")
    parser.add_argument("--jenkins", default=default_jenkins,
                        help="Jenkins credentials config (default: tools/config.yaml)")
    parser.add_argument("--dry-run", action="store_true", help="Print jobs without triggering")
    args = parser.parse_args()

    config = load_yaml(args.config)
    # Merge Jenkins creds from separate file if not already in jobs config
    if "jenkins" not in config:
        jenkins_config = load_yaml(args.jenkins)
        config["jenkins"] = jenkins_config["jenkins"]
    jobs = config.get("jobs", [])
    if not jobs:
        sys.exit("No jobs defined in config")

    execution = config.get("execution", {})
    mode = execution.get("mode", "sequential")
    fail_fast = execution.get("fail_fast", True)
    timeout = execution.get("timeout", 1800)

    if args.dry_run:
        print("Dry run — jobs that would be triggered:")
        for job in jobs:
            params = job.get("parameters", {})
            params_str = f" (params: {params})" if params else ""
            print(f"  - {job['name']}{params_str}")
        print(f"\nMode: {mode} | Fail fast: {fail_fast} | Timeout: {timeout}s")
        return

    base_url = config["jenkins"]["url"].rstrip("/")
    session = make_session(config)
    crumb = get_crumb(session, base_url)

    print(f"Running {len(jobs)} job(s) in {mode} mode\n")

    if mode == "parallel":
        results = run_parallel(session, base_url, jobs, crumb, timeout)
    else:
        results = run_sequential(session, base_url, jobs, crumb, timeout, fail_fast)

    print("\n--- Summary ---")
    all_ok = True
    for name, result, url in results:
        marker = "+" if result == "SUCCESS" else "-"
        print(f"  [{marker}] {name}: {result}")
        if url:
            print(f"       {url}")
        if result != "SUCCESS":
            all_ok = False

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
