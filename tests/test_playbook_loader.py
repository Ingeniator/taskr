import os
import pytest
import yaml

from services.playbook_loader import load_playbooks


@pytest.fixture()
def playbook_dir(tmp_path):
    return tmp_path


def _write_yaml(directory, filename, data):
    path = os.path.join(directory, filename)
    with open(path, "w") as f:
        yaml.dump(data, f)
    return path


class TestLoadPlaybooks:
    def test_valid_playbook(self, playbook_dir):
        _write_yaml(playbook_dir, "deploy.yml", {
            "name": "Deploy",
            "description": "Deploy to staging",
            "steps": [
                {"name": "Build", "run": "make build"},
                {"name": "Deploy", "run": "./deploy.sh"},
            ],
        })
        result = load_playbooks(str(playbook_dir))
        assert len(result) == 1
        pb = result[0]
        assert pb["name"] == "Deploy"
        assert pb["description"] == "Deploy to staging"
        assert pb["cwd"] == str(playbook_dir)
        assert len(pb["steps"]) == 2
        assert pb["file_path"] == os.path.abspath(os.path.join(playbook_dir, "deploy.yml"))

    def test_missing_name_skipped(self, playbook_dir):
        _write_yaml(playbook_dir, "bad.yml", {
            "steps": [{"name": "A", "run": "echo a"}],
        })
        assert load_playbooks(str(playbook_dir)) == []

    def test_missing_steps_skipped(self, playbook_dir):
        _write_yaml(playbook_dir, "bad.yml", {
            "name": "Bad",
        })
        assert load_playbooks(str(playbook_dir)) == []

    def test_empty_steps_skipped(self, playbook_dir):
        _write_yaml(playbook_dir, "bad.yml", {
            "name": "Bad",
            "steps": [],
        })
        assert load_playbooks(str(playbook_dir)) == []

    def test_step_missing_run_skipped(self, playbook_dir):
        _write_yaml(playbook_dir, "bad.yml", {
            "name": "Bad",
            "steps": [{"name": "Only name"}],
        })
        assert load_playbooks(str(playbook_dir)) == []

    def test_step_missing_name_skipped(self, playbook_dir):
        _write_yaml(playbook_dir, "bad.yml", {
            "name": "Bad",
            "steps": [{"run": "echo hi"}],
        })
        assert load_playbooks(str(playbook_dir)) == []

    def test_cwd_tilde_expansion(self, playbook_dir):
        _write_yaml(playbook_dir, "home.yml", {
            "name": "Home",
            "cwd": "~/myproject",
            "steps": [{"name": "A", "run": "echo a"}],
        })
        result = load_playbooks(str(playbook_dir))
        assert result[0]["cwd"] == os.path.expanduser("~/myproject")

    def test_cwd_relative_resolved_to_playbook_dir(self, playbook_dir):
        subdir = os.path.join(playbook_dir, "tools")
        os.makedirs(subdir, exist_ok=True)
        _write_yaml(playbook_dir, "rel.yml", {
            "name": "Relative",
            "cwd": "./tools",
            "steps": [{"name": "A", "run": "echo a"}],
        })
        result = load_playbooks(str(playbook_dir))
        assert result[0]["cwd"] == os.path.abspath(subdir)

    def test_default_description(self, playbook_dir):
        _write_yaml(playbook_dir, "minimal.yml", {
            "name": "Minimal",
            "steps": [{"name": "A", "run": "echo a"}],
        })
        result = load_playbooks(str(playbook_dir))
        assert result[0]["description"] == ""

    def test_sorted_by_name(self, playbook_dir):
        _write_yaml(playbook_dir, "z.yml", {
            "name": "Zulu",
            "steps": [{"name": "A", "run": "echo a"}],
        })
        _write_yaml(playbook_dir, "a.yml", {
            "name": "Alpha",
            "steps": [{"name": "A", "run": "echo a"}],
        })
        result = load_playbooks(str(playbook_dir))
        assert [p["name"] for p in result] == ["Alpha", "Zulu"]

    def test_nonexistent_dir(self):
        assert load_playbooks("/nonexistent/path/xyz") == []

    def test_yaml_extension_both(self, playbook_dir):
        _write_yaml(playbook_dir, "one.yml", {
            "name": "One",
            "steps": [{"name": "A", "run": "echo a"}],
        })
        _write_yaml(playbook_dir, "two.yaml", {
            "name": "Two",
            "steps": [{"name": "B", "run": "echo b"}],
        })
        result = load_playbooks(str(playbook_dir))
        assert len(result) == 2

    def test_non_yaml_files_ignored(self, playbook_dir):
        with open(os.path.join(playbook_dir, "readme.txt"), "w") as f:
            f.write("not a playbook")
        _write_yaml(playbook_dir, "ok.yml", {
            "name": "OK",
            "steps": [{"name": "A", "run": "echo a"}],
        })
        result = load_playbooks(str(playbook_dir))
        assert len(result) == 1

    def test_params_parsed(self, playbook_dir):
        _write_yaml(playbook_dir, "greet.yml", {
            "name": "Greet",
            "params": [
                {"name": "USER", "label": "Username", "default": "admin"},
            ],
            "steps": [{"name": "A", "run": "echo $USER"}],
        })
        result = load_playbooks(str(playbook_dir))
        assert len(result) == 1
        params = result[0]["params"]
        assert len(params) == 1
        assert params[0]["name"] == "USER"
        assert params[0]["label"] == "Username"
        assert params[0]["default"] == "admin"

    def test_param_missing_name_skips_playbook(self, playbook_dir):
        _write_yaml(playbook_dir, "bad_param.yml", {
            "name": "Bad Param",
            "params": [{"label": "No name key"}],
            "steps": [{"name": "A", "run": "echo a"}],
        })
        assert load_playbooks(str(playbook_dir)) == []

    def test_param_defaults(self, playbook_dir):
        _write_yaml(playbook_dir, "defaults.yml", {
            "name": "Defaults",
            "params": [{"name": "FOO"}],
            "steps": [{"name": "A", "run": "echo $FOO"}],
        })
        result = load_playbooks(str(playbook_dir))
        assert len(result) == 1
        p = result[0]["params"][0]
        assert p["label"] == "FOO"
        assert p["default"] == ""

    def test_no_params_defaults_to_empty_list(self, playbook_dir):
        _write_yaml(playbook_dir, "noparam.yml", {
            "name": "NoParam",
            "steps": [{"name": "A", "run": "echo a"}],
        })
        result = load_playbooks(str(playbook_dir))
        assert result[0]["params"] == []
