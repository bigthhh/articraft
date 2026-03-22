from __future__ import annotations

from pathlib import Path

from agent.harness import _minimal_scaffold_text


def test_base_scaffold_matches_harness_fallback() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    scaffold_path = repo_root / "scaffold.py"
    scaffold_text = scaffold_path.read_text(encoding="utf-8")

    assert scaffold_text == _minimal_scaffold_text(sdk_package="sdk")
    assert (
        "from sdk import ArticulatedObject, AssetContext, TestContext, TestReport" in scaffold_text
    )
    assert "def build_object_model() -> ArticulatedObject:" in scaffold_text
    assert "def run_tests() -> TestReport:" in scaffold_text
    assert "ctx.warn_if_articulation_origin_near_geometry(tol=0.015)" in scaffold_text
    assert "ctx.warn_if_part_geometry_disconnected()" in scaffold_text
    assert "ctx.check_articulation_overlaps(max_pose_samples=128)" in scaffold_text
    assert (
        "ctx.warn_if_overlaps(max_pose_samples=128, ignore_adjacent=True, ignore_fixed=True)"
        in scaffold_text
    )
    assert "Default broad sensor; do not remove. Tune params only if warranted." in scaffold_text


def test_hybrid_scaffold_matches_harness_fallback() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    scaffold_path = repo_root / "scaffold_hybrid.py"
    scaffold_text = scaffold_path.read_text(encoding="utf-8")

    assert scaffold_text == _minimal_scaffold_text(sdk_package="sdk_hybrid")
    assert (
        "from sdk_hybrid import ArticulatedObject, AssetContext, TestContext, TestReport"
        in scaffold_text
    )
    assert "def build_object_model() -> ArticulatedObject:" in scaffold_text
    assert "def run_tests() -> TestReport:" in scaffold_text
    assert "ctx.warn_if_articulation_origin_near_geometry(tol=0.015)" in scaffold_text
    assert "ctx.warn_if_part_geometry_disconnected()" in scaffold_text
    assert "ctx.check_articulation_overlaps(max_pose_samples=128)" in scaffold_text
    assert (
        "ctx.warn_if_overlaps(max_pose_samples=128, ignore_adjacent=True, ignore_fixed=True)"
        in scaffold_text
    )
    assert "Default broad sensor; do not remove. Tune params only if warranted." in scaffold_text
