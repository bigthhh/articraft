from __future__ import annotations

import sdk_hybrid
from sdk_hybrid.v0.cadquery import mesh_from_cadquery


def test_sdk_hybrid_exports() -> None:
    assert hasattr(sdk_hybrid, "ArticulatedObject")
    assert hasattr(sdk_hybrid, "ValidationError")
    assert hasattr(sdk_hybrid, "TestContext")
    assert hasattr(sdk_hybrid, "UnsupportedPartFinding")
    assert callable(mesh_from_cadquery)
    assert not hasattr(sdk_hybrid, "SectionLoftSpec")
    assert not hasattr(sdk_hybrid, "section_loft")
    assert not hasattr(sdk_hybrid, "repair_loft")
    assert not hasattr(sdk_hybrid, "ShellPartitionRegion")
    assert not hasattr(sdk_hybrid, "ShellPartitionSpec")
    assert not hasattr(sdk_hybrid, "partition_shell")
