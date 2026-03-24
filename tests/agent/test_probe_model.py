from __future__ import annotations

import asyncio
from pathlib import Path

from agent.tools.probe_model import ProbeModelTool


def _write_probe_fixture(script_path: Path, *, include_object_model: bool = True) -> None:
    lines = [
        "from __future__ import annotations",
        "",
        "from pathlib import Path",
        "",
        "from sdk import (",
        "    ArticulatedObject,",
        "    ArticulationType,",
        "    Box,",
        "    Cylinder,",
        "    MotionLimits,",
        "    Origin,",
        "    TestContext,",
        ")",
        "",
        "HERE = Path(__file__).resolve().parent",
        "model = ArticulatedObject(name='probe_fixture')",
        "panel = model.part('panel')",
        "panel.visual(Box((1.0, 0.6, 0.08)), origin=Origin(xyz=(0.0, 0.0, 0.04)), name='panel_body')",
        "panel.visual(Cylinder(radius=0.06, length=0.04), origin=Origin(xyz=(0.0, 0.0, 0.10)), name='knob')",
        "keys = model.part('keys')",
        "keys.visual(Box((0.10, 0.20, 0.04)), origin=Origin(xyz=(-0.24, 0.0, 0.02)), name='key_1')",
        "keys.visual(Box((0.10, 0.20, 0.04)), origin=Origin(xyz=(0.00, 0.0, 0.02)), name='key_2')",
        "keys.visual(Box((0.10, 0.20, 0.04)), origin=Origin(xyz=(0.24, 0.0, 0.02)), name='key_3')",
        "arm = model.part('arm')",
        "arm.visual(Box((0.30, 0.08, 0.08)), origin=Origin(xyz=(0.15, 0.0, 0.04)), name='arm_body')",
        "model.articulation(",
        "    'panel_to_keys',",
        "    ArticulationType.FIXED,",
        "    parent=panel,",
        "    child=keys,",
        "    origin=Origin(xyz=(0.0, 0.0, 0.08)),",
        ")",
        "model.articulation(",
        "    'panel_to_arm',",
        "    ArticulationType.REVOLUTE,",
        "    parent=panel,",
        "    child=arm,",
        "    origin=Origin(xyz=(0.45, 0.0, 0.08)),",
        "    axis=(0.0, 0.0, 1.0),",
        "    motion_limits=MotionLimits(lower=-0.5, upper=0.5, effort=2.0, velocity=1.0),",
        ")",
        "",
    ]
    if include_object_model:
        lines.extend(
            [
                "object_model = model",
                "",
            ]
        )
    lines.extend(
        [
            "def run_tests():",
            "    ctx = TestContext(object_model, asset_root=HERE)",
            "    return ctx.report()",
        ]
    )
    script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _run_probe(
    script_path: Path,
    code: str,
    *,
    timeout_ms: int = 1000,
    include_stdout: bool = False,
) -> dict[str, object]:
    tool = ProbeModelTool(sdk_package="sdk")
    invocation = await tool.build(
        {
            "file_path": str(script_path),
            "code": code,
            "timeout_ms": timeout_ms,
            "include_stdout": include_stdout,
        }
    )
    result = await invocation.execute()
    assert result.error is None
    assert isinstance(result.output, dict)
    return result.output


def test_probe_model_returns_structured_measurements(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_probe_fixture(script_path)

    output = asyncio.run(
        _run_probe(
            script_path,
            "\n".join(
                [
                    "panel = part('panel')",
                    "knob = visual('panel', 'knob')",
                    "emit({",
                    "    'part_names': [name(item) for item in parts()],",
                    "    'knob_mount': mount_report(knob, panel),",
                    "})",
                ]
            ),
        )
    )

    assert output["ok"] is True
    result = output["result"]
    assert isinstance(result, dict)
    assert result["part_names"] == ["panel", "keys", "arm"]
    knob_mount = result["knob_mount"]
    assert knob_mount["metric_kind"] == "mount_review"
    assert knob_mount["child"] == {"part": "panel", "visual": "knob"}
    assert knob_mount["parent"] == {"part": "panel"}


def test_probe_model_captures_stdout_when_requested(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_probe_fixture(script_path)

    output = asyncio.run(
        _run_probe(
            script_path,
            "print('debug line'); emit({'ok': True})",
            include_stdout=True,
        )
    )

    assert output["ok"] is True
    assert "debug line" in output["stdout"]


def test_probe_model_missing_emit_fails_clearly(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_probe_fixture(script_path)

    output = asyncio.run(_run_probe(script_path, "part('panel')"))

    assert output["ok"] is False
    assert output["error"]["type"] == "emit_contract"
    assert "emit(value) was not called" in output["error"]["message"]


def test_probe_model_double_emit_fails_clearly(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_probe_fixture(script_path)

    output = asyncio.run(_run_probe(script_path, "emit(1)\nemit(2)"))

    assert output["ok"] is False
    assert output["error"]["type"] == "emit_contract"
    assert "exactly once" in output["error"]["message"]


def test_probe_model_snippet_exception_fails_clearly(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_probe_fixture(script_path)

    output = asyncio.run(_run_probe(script_path, "raise RuntimeError('boom')"))

    assert output["ok"] is False
    assert output["error"]["type"] == "snippet_exception"
    assert "boom" in output["error"]["message"]


def test_probe_model_timeout_fails_clearly(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_probe_fixture(script_path)

    output = asyncio.run(
        _run_probe(
            script_path,
            "import time\ntime.sleep(0.5)\nemit({'done': True})",
            timeout_ms=100,
        )
    )

    assert output["ok"] is False
    assert output["error"]["type"] == "timeout"


def test_probe_model_missing_object_model_fails_clearly(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_probe_fixture(script_path, include_object_model=False)

    output = asyncio.run(_run_probe(script_path, "emit({'ok': True})"))

    assert output["ok"] is False
    assert output["error"]["type"] == "load_failure"
    assert "`object_model`" in output["error"]["message"]


def test_probe_model_lookup_failure_is_clear(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_probe_fixture(script_path)

    output = asyncio.run(_run_probe(script_path, "emit(summary(part('missing')))"))

    assert output["ok"] is False
    assert output["error"]["type"] == "lookup_failure"
    assert "Unknown part" in output["error"]["message"]


def test_probe_model_non_serializable_result_is_clear(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_probe_fixture(script_path)

    output = asyncio.run(_run_probe(script_path, "emit({'bad': {1, 2, 3}})"))

    assert output["ok"] is False
    assert output["error"]["type"] == "non_serializable_result"


def test_probe_model_supports_layout_and_pose_sampling(tmp_path: Path) -> None:
    script_path = tmp_path / "model.py"
    _write_probe_fixture(script_path)

    output = asyncio.run(
        _run_probe(
            script_path,
            "\n".join(
                [
                    "keys = [visual('keys', name) for name in ('key_1', 'key_2', 'key_3')]",
                    "emit({",
                    "    'layout': layout_report(keys, axis='x'),",
                    "    'poses': sample_poses(max_samples=4, seed=1),",
                    "})",
                ]
            ),
        )
    )

    assert output["ok"] is True
    result = output["result"]
    layout = result["layout"]
    assert layout["metric_kind"] == "layout_review"
    assert layout["count"] == 3
    assert len(layout["pitches"]) == 2
    poses = result["poses"]
    assert poses
    assert isinstance(poses, list)
