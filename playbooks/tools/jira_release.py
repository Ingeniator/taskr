#!/usr/bin/env python3
"""Jira release helper: find/create release ticket, link issues, transition."""

import argparse
import json
import os
import sys

import requests
import yaml


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def make_session(config):
    jira = config["jira"]
    token = jira.get("token") or os.environ.get("JIRA_API_TOKEN", "")
    if not token:
        sys.exit("Error: Jira API token not set in config or JIRA_API_TOKEN env var")

    session = requests.Session()
    session.auth = (jira["user"], token)
    session.headers["Content-Type"] = "application/json"
    return session


def search_issues(session, base_url, jql, max_results=50):
    resp = session.get(
        f"{base_url}/rest/api/2/search",
        params={"jql": jql, "maxResults": max_results},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("issues", [])


def create_issue(session, base_url, project, summary, issue_type, description=""):
    payload = {
        "fields": {
            "project": {"key": project},
            "summary": summary,
            "issuetype": {"name": issue_type},
            "description": description,
        }
    }
    resp = session.post(
        f"{base_url}/rest/api/2/issue",
        data=json.dumps(payload),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def link_issue(session, base_url, inward_key, outward_key, link_type="Relates"):
    payload = {
        "type": {"name": link_type},
        "inwardIssue": {"key": inward_key},
        "outwardIssue": {"key": outward_key},
    }
    resp = session.post(
        f"{base_url}/rest/api/2/issueLink",
        data=json.dumps(payload),
        timeout=15,
    )
    resp.raise_for_status()


def get_transitions(session, base_url, issue_key):
    resp = session.get(
        f"{base_url}/rest/api/2/issue/{issue_key}/transitions",
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("transitions", [])


def do_transition(session, base_url, issue_key, transition_id):
    payload = {"transition": {"id": transition_id}}
    resp = session.post(
        f"{base_url}/rest/api/2/issue/{issue_key}/transitions",
        data=json.dumps(payload),
        timeout=15,
    )
    resp.raise_for_status()


# -- Subcommands --

def cmd_find_or_create(session, base_url, args):
    project = args.project
    version = args.version
    issue_type = args.issue_type

    jql = f'project = {project} AND issuetype = "{issue_type}" AND summary ~ "Release {version}"'
    print(f"Searching: {jql}")
    issues = search_issues(session, base_url, jql, max_results=1)

    if issues:
        key = issues[0]["key"]
        print(f"Found existing release ticket: {key}")
    else:
        summary = f"Release {version}"
        description = f"Release ticket for version {version}."
        result = create_issue(session, base_url, project, summary, issue_type, description)
        key = result["key"]
        print(f"Created release ticket: {key}")

    # Write key to file so subsequent steps can read it
    output = os.environ.get("RELEASE_TICKET_FILE", "/tmp/release_ticket_key.txt")
    with open(output, "w") as f:
        f.write(key)
    print(f"Ticket key written to {output}")


def cmd_link_issues(session, base_url, args):
    ticket_file = os.environ.get("RELEASE_TICKET_FILE", "/tmp/release_ticket_key.txt")
    with open(ticket_file) as f:
        release_key = f.read().strip()

    jql = args.jql
    link_type = args.link_type
    print(f"Linking issues matching: {jql}")
    print(f"Release ticket: {release_key}")

    issues = search_issues(session, base_url, jql)
    if not issues:
        print("No issues found matching JQL.")
        return

    for issue in issues:
        key = issue["key"]
        if key == release_key:
            continue
        try:
            link_issue(session, base_url, release_key, key, link_type)
            print(f"  Linked {key}")
        except requests.HTTPError as e:
            print(f"  Failed to link {key}: {e}")

    print(f"Linked {len(issues)} issue(s) to {release_key}")


def cmd_transition(session, base_url, args):
    ticket_file = os.environ.get("RELEASE_TICKET_FILE", "/tmp/release_ticket_key.txt")
    with open(ticket_file) as f:
        release_key = f.read().strip()

    target = args.status
    print(f"Transitioning {release_key} to '{target}'")

    transitions = get_transitions(session, base_url, release_key)
    match = None
    for t in transitions:
        if t["name"].lower() == target.lower():
            match = t
            break

    if not match:
        available = ", ".join(t["name"] for t in transitions)
        sys.exit(f"Transition '{target}' not available. Available: {available}")

    do_transition(session, base_url, release_key, match["id"])
    print(f"Transitioned {release_key} to '{target}'")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_config = os.path.join(script_dir, "config.yaml")

    parser = argparse.ArgumentParser(description="Jira release helper")
    parser.add_argument("--config", default=default_config, help="Config file path")
    sub = parser.add_subparsers(dest="command", required=True)

    # find-or-create
    fc = sub.add_parser("find-or-create", help="Find or create a release ticket")
    fc.add_argument("--project", default="PROJ", help="Jira project key")
    fc.add_argument("--version", required=True, help="Release version")
    fc.add_argument("--issue-type", default="Release", help="Issue type for release ticket")

    # link-issues
    li = sub.add_parser("link-issues", help="Link issues by JQL to release ticket")
    li.add_argument("--jql", required=True, help="JQL to find issues")
    li.add_argument("--link-type", default="Relates", help="Issue link type name")

    # transition
    tr = sub.add_parser("transition", help="Transition the release ticket")
    tr.add_argument("--status", default="Done", help="Target status name")

    args = parser.parse_args()

    config = load_config(args.config)
    base_url = config["jira"]["url"].rstrip("/")
    session = make_session(config)

    if args.command == "find-or-create":
        cmd_find_or_create(session, base_url, args)
    elif args.command == "link-issues":
        cmd_link_issues(session, base_url, args)
    elif args.command == "transition":
        cmd_transition(session, base_url, args)


if __name__ == "__main__":
    main()
