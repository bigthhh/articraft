from __future__ import annotations

from sdk._core.v0.mesh import BoxGeometry, mesh_from_geometry
from sdk._core.v0.viewer_assets import convert_urdf_visual_meshes_to_glb


def test_convert_urdf_visual_meshes_to_glb_resolves_legacy_mesh_prefix(tmp_path) -> None:
    mesh_from_geometry(
        BoxGeometry((1.0, 1.0, 1.0)),
        tmp_path / "assets" / "meshes" / "part.obj",
    )

    urdf_xml = (
        "<robot name='legacy'>"
        "<link name='base'>"
        "<visual><geometry><mesh filename='meshes/part.obj'/></geometry></visual>"
        "</link>"
        "</robot>"
    )

    converted_xml, warnings = convert_urdf_visual_meshes_to_glb(
        urdf_xml,
        asset_root=tmp_path,
    )

    assert warnings == []
    assert "meshes/part.glb" in converted_xml
    assert (tmp_path / "assets" / "meshes" / "part.glb").exists()
