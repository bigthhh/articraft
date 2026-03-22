"""Shared internal SDK v0 implementation."""

# ruff: noqa: F401
from .articulated_object import ArticulatedObject
from .assets import AssetContext
from .errors import SDKError, ValidationError
from .placement import (
    SurfaceFrame,
    SurfaceWrapMapping,
    align_centers_xy,
    part_local_aabb,
    place_in_front_of,
    place_on_face,
    place_on_face_uv,
    place_on_surface,
    place_on_top,
    proud_for_flush_mount,
    surface_frame,
    wrap_mesh_onto_surface,
    wrap_profile_onto_surface,
)
from .testing import TestContext, TestFailure, TestReport
from .types import (
    Articulation,
    ArticulationType,
    Box,
    Cylinder,
    Inertia,
    Inertial,
    Material,
    Mesh,
    MotionLimits,
    MotionProperties,
    Origin,
    Part,
    Sphere,
    Visual,
)
