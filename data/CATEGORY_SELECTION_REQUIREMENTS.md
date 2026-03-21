# Category Selection Requirements

This document defines the bar for adding new categories to `datasets/final_10k`.

The goal is not just to add interesting ideas. New categories must be:

- representable as a believable articulated object in URDF
- implementable with this repository's SDK stack
- distinct enough to justify a separate category in the taxonomy

## Hard Requirements

Every proposed category should satisfy all of the following.

### 1. URDF-Valid Representation

The category must map cleanly to the articulation model supported by this repo:

- rigid parts connected by explicit joints
- `revolute`, `continuous`, `prismatic`, or `fixed` motion
- tree-structured kinematics

Categories should be rejected if their core behavior depends on mechanisms that URDF does not represent honestly or directly, such as:

- closed kinematic loops
- cable or belt coupling
- pulley routing
- helical screw motion as the primary mechanism
- contact-driven motion
- ratcheting, indexing, or intermittent locking behavior
- gear-train coupling that requires linked motion constraints

Examples of risky categories:

- cable-and-pulley lifts
- Geneva drives
- ratchet-and-pawl mechanisms
- differentials
- true cam-follower systems
- true four-bar or scissor mechanisms if the closed loop is essential

If the defining mechanism cannot be represented faithfully without faking the behavior, the category is not a good fit.

### 2. Implementable In Our SDK

The category must be practical to author with `sdk` or `sdk_hybrid`.

For `hybrid_cad` categories, prefer:

- hard-surface geometry
- explicit rigid members, brackets, rails, hubs, and housings
- simple joint topology with clear parent/child structure
- parts that benefit from CAD-style dimensional modeling

Avoid categories that require:

- soft-body behavior
- deformable materials as the main visual identity
- simulation-only constraints
- complex mechanical coupling not expressible through explicit authored joints

If a category would require unusual hacks to pass validation or would be consistently fragile in QC, it should not be added.

### 3. Taxonomically Distinct

A new category must not be just a thin variant of an existing one.

Reject categories that are only:

- an existing category with one extra joint
- a subset of an existing category
- a count variant of an existing topology
- an attachment variant of an existing mechanism
- a relabeling of an already-covered object class

Examples of weak additions:

- adding another revolute-chain category only because it has one more segment
- adding a stage category that is just `Orthogonal XY stage` plus a small head
- adding a finger or branching-tree category that differs only by count

New categories should introduce at least one of:

- a meaningfully different articulation topology
- a meaningfully different support structure
- a meaningfully different mechanism archetype
- a clearly different object identity

## Placement Rules

### Mechanism-First Block

The top block of the tracker is reserved for mechanism/topology categories.

These should usually be:

- abstract or semi-abstract mechanical structures
- structurally legible without relying on product styling
- strong fits for `hybrid_cad`

Examples already in this family:

- joint chains
- gimbal modules
- telescoping slides
- Cartesian stages
- branching articulated structures

### Object Categories

Object-like categories belong later in the tracker, even if they contain articulation.

Examples:

- appliances
- furniture
- vehicles
- consumer products
- lighting fixtures

For example, `Ceiling fan` belongs in the object section, not the mechanism block.

## Decision Checklist

Before adding a category, check:

1. Is the core motion representable with explicit URDF joints and tree kinematics?
2. Can we build it cleanly with `sdk` or `sdk_hybrid` without special hacks?
3. Is it meaningfully different from the categories already in `10k_dataset_tracker.csv`?
4. Does it belong in the mechanism block or the object block?
5. Is the chosen `target sdk version` aligned with the category's geometry style?

If any of these answers is "no" or "not really", the category should usually be rejected or renamed.

## Practical Defaults

- Use `hybrid_cad` for mechanism-first categories with hard-surface, CAD-friendly geometry.
- Use `base` for object categories where canonical product identity matters more than abstract mechanism topology.
- Initialize newly added categories with `Count=0` unless accepted items already exist.
