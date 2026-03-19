from __future__ import annotations

import sdk


def test_sdk_exports() -> None:
    assert hasattr(sdk, "ArticulatedObject")
    assert hasattr(sdk, "CapsuleGeometry")
    assert hasattr(sdk, "DomeGeometry")
    assert hasattr(sdk, "ValidationError")
    assert hasattr(sdk, "TestContext")
    assert hasattr(sdk, "SectionLoftSpec")
    assert hasattr(sdk, "section_loft")
    assert hasattr(sdk, "repair_loft")
    assert hasattr(sdk, "ShellPartitionRegion")
    assert hasattr(sdk, "ShellPartitionSpec")
    assert hasattr(sdk, "partition_shell")
