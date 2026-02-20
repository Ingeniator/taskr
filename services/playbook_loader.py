import os
import logging

import yaml

logger = logging.getLogger(__name__)


def load_playbooks(playbook_dir: str) -> list[dict]:
    """Load all YAML playbooks from a directory.

    Returns a sorted list of validated playbook dicts, each augmented with
    ``file_path`` (absolute) and default values for optional fields.
    """
    playbook_dir = os.path.expanduser(playbook_dir)
    if not os.path.isdir(playbook_dir):
        return []

    playbooks = []
    for name in sorted(os.listdir(playbook_dir)):
        if not (name.endswith(".yml") or name.endswith(".yaml")):
            continue
        path = os.path.join(playbook_dir, name)
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except Exception as e:
            logger.warning("Skipping %s: %s", name, e)
            continue

        if not isinstance(data, dict):
            logger.warning("Skipping %s: not a YAML mapping", name)
            continue

        if "name" not in data:
            logger.warning("Skipping %s: missing 'name'", name)
            continue

        steps = data.get("steps")
        if not isinstance(steps, list) or len(steps) == 0:
            logger.warning("Skipping %s: missing or empty 'steps'", name)
            continue

        valid = True
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                logger.warning("Skipping %s: step %d is not a mapping", name, i)
                valid = False
                break
            if "name" not in step or "run" not in step:
                logger.warning("Skipping %s: step %d missing 'name' or 'run'", name, i)
                valid = False
                break
        if not valid:
            continue

        # Parse optional params
        raw_params = data.get("params", [])
        params = []
        if isinstance(raw_params, list):
            params_valid = True
            for p in raw_params:
                if not isinstance(p, dict) or "name" not in p:
                    logger.warning("Skipping %s: param missing 'name'", name)
                    params_valid = False
                    break
                params.append({
                    "name": p["name"],
                    "label": p.get("label", p["name"]),
                    "default": p.get("default", ""),
                })
            if not params_valid:
                continue

        cwd = data.get("cwd", playbook_dir)
        cwd = os.path.expanduser(cwd)
        if not os.path.isabs(cwd):
            cwd = os.path.join(playbook_dir, cwd)
        cwd = os.path.abspath(cwd)

        playbooks.append({
            "name": data["name"],
            "description": data.get("description", ""),
            "cwd": cwd,
            "steps": steps,
            "params": params,
            "file_path": os.path.abspath(path),
        })

    playbooks.sort(key=lambda p: p["name"])
    return playbooks
