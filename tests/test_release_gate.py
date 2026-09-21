from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE = ROOT / "conformance" / "valid-profiled-allow-v0.1.jsonl"


def _python_env() -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("PYTHONPATH")
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src if not current else src + os.pathsep + current
    return env


def _run(*argv: str, cwd: Path = ROOT, env: dict[str, str] | None = None):
    return subprocess.run(
        list(argv),
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def test_examples_execute_from_clean_source_layout():
    env = _python_env()
    for relative in (
        "examples/basic_lifecycle.py",
        "examples/retry_delayed_confirmation.py",
    ):
        result = _run(sys.executable, relative, env=env)
        assert result.returncode == 0, result.stderr


def test_cli_release_surface_against_public_conformance_vector():
    env = _python_env()
    commands = (
        ("validate", str(CONFORMANCE)),
        ("summary", str(CONFORMANCE)),
        ("assess-decision", str(CONFORMANCE), "decision-1"),
        ("bundle", str(CONFORMANCE)),
    )
    for command in commands:
        result = _run(
            sys.executable,
            "-m",
            "ddc_action_lifecycle.cli",
            *command,
            env=env,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        parsed = json.loads(result.stdout)
        if command[0] == "validate":
            assert parsed["valid"] is True
        if command[0] == "assess-decision":
            assert parsed["assessment"]["status"] == "VALID"
            assert parsed["next_transition"]["disposition"] == "ALLOW"


def test_wheel_build_and_installed_console_script(tmp_path):
    pip_probe = _run(sys.executable, "-m", "pip", "--version")
    if pip_probe.returncode != 0:
        pytest.skip(
            "verification executor lacks pip; package build/install remains a separate release gate"
        )

    wheel_dir = tmp_path / "wheel"
    install_dir = tmp_path / "install"
    wheel_dir.mkdir()
    install_dir.mkdir()

    build = _run(
        sys.executable,
        "-m",
        "pip",
        "wheel",
        ".",
        "--no-deps",
        "--no-build-isolation",
        "--no-index",
        "-w",
        str(wheel_dir),
    )
    assert build.returncode == 0, build.stderr or build.stdout

    wheels = list(wheel_dir.glob("ddc_action_lifecycle-*.whl"))
    assert len(wheels) == 1
    wheel = wheels[0]

    with zipfile.ZipFile(wheel) as archive:
        entry_points = [
            name for name in archive.namelist() if name.endswith(".dist-info/entry_points.txt")
        ]
        assert len(entry_points) == 1
        content = archive.read(entry_points[0]).decode("utf-8")
        assert "ddc-lifecycle = ddc_action_lifecycle.cli:main" in content

    install = _run(
        sys.executable,
        "-m",
        "pip",
        "install",
        "--no-deps",
        "--no-index",
        "--target",
        str(install_dir),
        str(wheel),
    )
    assert install.returncode == 0, install.stderr or install.stdout

    installed_env = os.environ.copy()
    installed_env["PYTHONPATH"] = str(install_dir)
    smoke = _run(
        sys.executable,
        "-m",
        "ddc_action_lifecycle.cli",
        "validate",
        str(CONFORMANCE),
        env=installed_env,
    )
    assert smoke.returncode == 0, smoke.stderr or smoke.stdout
    assert json.loads(smoke.stdout)["valid"] is True
