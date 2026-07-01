---
title: 'Six-Axis Robot Arm with CadQuery Housings and a Parallel Gripper'
description: 'Base SDK serial manipulator: a six-joint revolute chain of CadQuery filleted-shell link housings on a turntable base, ending in a two-finger parallel gripper with prismatic jaws. Shows how to keep a high part and joint count while authoring each visible link as a real machined housing instead of a stack of bare primitives.'
tags:
  - sdk
  - base sdk
  - robot arm
  - manipulator
  - six axis
  - serial chain
  - revolute chain
  - gripper
  - parallel jaw
  - prismatic
  - cadquery
  - filleted housing
  - shell
  - high part count
---
# Six-Axis Robot Arm with CadQuery Housings and a Parallel Gripper

A worked example of a *high-complexity* assembly that still reads as a real machine. Two ideas worth reusing:

- **Serial-chain topology keeps a long joint count clean.** Each link is the child of the previous one, so the tree stays valid and adjacent links only touch at their shared joint (silenced with scoped `allow_overlap`). Adding axes is just extending the chain.
- **CadQuery for the visible link housings, not bare primitives.** Every link is a filleted shell box with a cut cable channel, authored with a small helper and reused at each joint. This is what makes the arm read as machined castings rather than a stack of blocks.

Authoring convention: all geometry is written in **world coordinates at the rest pose**, and each articulation `origin` is the joint's **world location** — the SDK derives the relative transforms. Joint axes alternate (yaw `Z`, then pitch `Y`) the way a real manipulator's wrist is built.

```python
from __future__ import annotations

import cadquery as cq

from sdk import (
    ArticulatedObject,
    ArticulationType,
    Box,
    Cylinder,
    Inertial,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
    mesh_from_cadquery,
)


def _link_housing(width: float, depth: float, height: float, fillet: float, name: str):
    """A filleted shell-style link housing with a cut cable channel down one face."""
    solid = (
        cq.Workplane("XY")
        .box(width, depth, height)
        .edges("|Z")
        .fillet(fillet)
    )
    channel = (
        cq.Workplane("XY")
        .box(width * 0.45, depth * 0.18, height * 0.92)
        .translate((0.0, depth * 0.5, 0.0))
    )
    return mesh_from_cadquery(solid.cut(channel), name)


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject(name="six_axis_robot_arm")

    cast_grey = model.material("cast_grey", rgba=(0.62, 0.64, 0.67, 1.0))
    joint_black = model.material("joint_black", rgba=(0.10, 0.10, 0.12, 1.0))
    safety_orange = model.material("safety_orange", rgba=(0.95, 0.45, 0.10, 1.0))

    # --- Root: bolted base + shoulder turntable plate ---
    base = model.part("base")
    base.visual(
        mesh_from_cadquery(
            cq.Workplane("XY").cylinder(0.06, 0.10).edges(">Z").fillet(0.01),
            "base_casting",
        ),
        origin=Origin(xyz=(0.0, 0.0, 0.03)),
        material=cast_grey,
        name="base_casting",
    )
    base.visual(
        Cylinder(radius=0.07, length=0.03),
        origin=Origin(xyz=(0.0, 0.0, 0.075)),
        material=joint_black,
        name="turntable_collar",
    )
    base.inertial = Inertial.from_geometry(
        Cylinder(radius=0.10, length=0.09),
        mass=6.0,
        origin=Origin(xyz=(0.0, 0.0, 0.045)),
    )

    # --- Link 1: shoulder turret (yaw about Z) ---
    shoulder = model.part("shoulder")
    shoulder.visual(
        _link_housing(0.14, 0.13, 0.12, 0.02, "shoulder_housing"),
        origin=Origin(xyz=(0.0, 0.0, 0.15)),
        material=cast_grey,
        name="shoulder_housing",
    )

    # --- Link 2: upper arm (pitch about Y) ---
    upper_arm = model.part("upper_arm")
    upper_arm.visual(
        _link_housing(0.10, 0.11, 0.30, 0.02, "upper_arm_housing"),
        origin=Origin(xyz=(0.0, 0.0, 0.36)),
        material=cast_grey,
        name="upper_arm_housing",
    )

    # --- Link 3: forearm (pitch about Y) ---
    forearm = model.part("forearm")
    forearm.visual(
        _link_housing(0.085, 0.095, 0.24, 0.018, "forearm_housing"),
        origin=Origin(xyz=(0.0, 0.0, 0.63)),
        material=cast_grey,
        name="forearm_housing",
    )

    # --- Link 4: wrist roll (about Z) ---
    wrist_roll = model.part("wrist_roll")
    wrist_roll.visual(
        mesh_from_cadquery(
            cq.Workplane("XY").cylinder(0.07, 0.045).edges(">Z").fillet(0.006),
            "wrist_roll_housing",
        ),
        origin=Origin(xyz=(0.0, 0.0, 0.785)),
        material=cast_grey,
        name="wrist_roll_housing",
    )

    # --- Link 5: wrist pitch (about Y) ---
    wrist_pitch = model.part("wrist_pitch")
    wrist_pitch.visual(
        _link_housing(0.07, 0.08, 0.06, 0.012, "wrist_pitch_housing"),
        origin=Origin(xyz=(0.0, 0.0, 0.85)),
        material=joint_black,
        name="wrist_pitch_housing",
    )

    # --- Link 6: tool flange (roll about Z) + gripper body ---
    flange = model.part("flange")
    flange.visual(
        Cylinder(radius=0.04, length=0.03),
        origin=Origin(xyz=(0.0, 0.0, 0.90)),
        material=joint_black,
        name="tool_flange",
    )
    flange.visual(
        Box((0.08, 0.05, 0.03)),
        origin=Origin(xyz=(0.0, 0.0, 0.925)),
        material=cast_grey,
        name="gripper_body",
    )

    # --- Parallel gripper jaws (prismatic, open/close along X) ---
    finger_left = model.part("finger_left")
    finger_left.visual(
        Box((0.012, 0.04, 0.06)),
        origin=Origin(xyz=(-0.03, 0.0, 0.965)),
        material=safety_orange,
        name="finger_left",
    )
    finger_right = model.part("finger_right")
    finger_right.visual(
        Box((0.012, 0.04, 0.06)),
        origin=Origin(xyz=(0.03, 0.0, 0.965)),
        material=safety_orange,
        name="finger_right",
    )

    # --- Articulations: a six-joint serial chain + two gripper jaws ---
    model.articulation(
        "j1_base_yaw",
        ArticulationType.REVOLUTE,
        parent=base,
        child=shoulder,
        origin=Origin(xyz=(0.0, 0.0, 0.09)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(lower=-2.9, upper=2.9, effort=120.0, velocity=2.0),
    )
    model.articulation(
        "j2_shoulder_pitch",
        ArticulationType.REVOLUTE,
        parent=shoulder,
        child=upper_arm,
        origin=Origin(xyz=(0.0, 0.0, 0.21)),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(lower=-1.9, upper=1.9, effort=110.0, velocity=2.0),
    )
    model.articulation(
        "j3_elbow_pitch",
        ArticulationType.REVOLUTE,
        parent=upper_arm,
        child=forearm,
        origin=Origin(xyz=(0.0, 0.0, 0.51)),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(lower=-2.5, upper=2.5, effort=80.0, velocity=2.5),
    )
    model.articulation(
        "j4_wrist_roll",
        ArticulationType.REVOLUTE,
        parent=forearm,
        child=wrist_roll,
        origin=Origin(xyz=(0.0, 0.0, 0.75)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(lower=-3.1, upper=3.1, effort=40.0, velocity=3.0),
    )
    model.articulation(
        "j5_wrist_pitch",
        ArticulationType.REVOLUTE,
        parent=wrist_roll,
        child=wrist_pitch,
        origin=Origin(xyz=(0.0, 0.0, 0.82)),
        axis=(0.0, 1.0, 0.0),
        motion_limits=MotionLimits(lower=-2.0, upper=2.0, effort=30.0, velocity=3.0),
    )
    model.articulation(
        "j6_flange_roll",
        ArticulationType.REVOLUTE,
        parent=wrist_pitch,
        child=flange,
        origin=Origin(xyz=(0.0, 0.0, 0.88)),
        axis=(0.0, 0.0, 1.0),
        motion_limits=MotionLimits(lower=-3.1, upper=3.1, effort=20.0, velocity=3.5),
    )
    model.articulation(
        "jaw_left",
        ArticulationType.PRISMATIC,
        parent=flange,
        child=finger_left,
        origin=Origin(xyz=(-0.03, 0.0, 0.94)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(lower=0.0, upper=0.022, effort=15.0, velocity=0.1),
    )
    model.articulation(
        "jaw_right",
        ArticulationType.PRISMATIC,
        parent=flange,
        child=finger_right,
        origin=Origin(xyz=(0.03, 0.0, 0.94)),
        axis=(-1.0, 0.0, 0.0),
        motion_limits=MotionLimits(lower=0.0, upper=0.022, effort=15.0, velocity=0.1),
    )

    return model


def run_tests() -> TestReport:
    ctx = TestContext(object_model)

    # Adjacent links share their joint region; silence the local seam overlaps.
    seam_pairs = [
        ("base", "shoulder", "turntable_collar", "shoulder_housing"),
        ("shoulder", "upper_arm", "shoulder_housing", "upper_arm_housing"),
        ("upper_arm", "forearm", "upper_arm_housing", "forearm_housing"),
        ("forearm", "wrist_roll", "forearm_housing", "wrist_roll_housing"),
        ("wrist_roll", "wrist_pitch", "wrist_roll_housing", "wrist_pitch_housing"),
        ("wrist_pitch", "flange", "wrist_pitch_housing", "tool_flange"),
    ]
    for parent_name, child_name, elem_a, elem_b in seam_pairs:
        ctx.allow_overlap(
            object_model.get_part(parent_name),
            object_model.get_part(child_name),
            elem_a=elem_a,
            elem_b=elem_b,
            reason="Adjacent serial-chain links meet at their shared joint.",
        )

    flange_part = object_model.get_part("flange")
    for finger_name in ("finger_left", "finger_right"):
        ctx.allow_overlap(
            flange_part,
            object_model.get_part(finger_name),
            elem_a="gripper_body",
            elem_b=finger_name,
            reason="Gripper jaws are seated in the gripper body rails.",
        )

    # Yawing the base must swing the tool flange out of the X... plane.
    flange_rest = ctx.part_world_position(flange_part)
    with ctx.pose(j1_base_yaw=1.5, j2_shoulder_pitch=1.0):
        flange_swung = ctx.part_world_position(flange_part)
    ctx.check(
        "arm_reaches_out_when_articulated",
        flange_rest is not None
        and flange_swung is not None
        and abs(flange_swung[0] - flange_rest[0]) > 0.05,
        details=f"rest={flange_rest}, swung={flange_swung}",
    )

    # Closing the gripper must bring the two jaws together.
    with ctx.pose(jaw_left=0.0, jaw_right=0.0):
        open_left = ctx.part_world_position(object_model.get_part("finger_left"))
        open_right = ctx.part_world_position(object_model.get_part("finger_right"))
    with ctx.pose(jaw_left=0.02, jaw_right=0.02):
        closed_left = ctx.part_world_position(object_model.get_part("finger_left"))
        closed_right = ctx.part_world_position(object_model.get_part("finger_right"))
    if None not in (open_left, open_right, closed_left, closed_right):
        ctx.check(
            "gripper_closes",
            abs(closed_left[0] - closed_right[0]) < abs(open_left[0] - open_right[0]),
            details=f"open_gap={abs(open_left[0] - open_right[0]):.4f}, "
            f"closed_gap={abs(closed_left[0] - closed_right[0]):.4f}",
        )

    return ctx.report()


object_model = build_object_model()
```
