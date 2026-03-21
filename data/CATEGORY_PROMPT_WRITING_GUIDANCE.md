# Category Prompt Writing Guidance

This document defines how to write category prompts for `datasets/final_10k` so generated objects are visually coherent, mechanically believable, and clean in the viewer.

The goal is not to maximize the number of articulations. The goal is to maximize object realism and readable structure while preserving the right motions for the category.

## Primary Goal

Prompts should produce objects that:

- look like a believable instance of the category at first glance
- have a strong, coherent silhouette and clear structural hierarchy
- keep moving parts attached to obvious supports and pivots
- avoid floating-looking parts, disconnected subassemblies, and arbitrary joints
- use articulation to express the object, not to replace the object

## Core Principle

Prompt writing should follow this priority order:

1. Canonical object identity
2. Structural coherence
3. Realistic attachment and support
4. Key articulation
5. Secondary articulation only if it is standard for the category

If a prompt makes the model choose between adding more joints and preserving a believable object, the prompt is wrong.

## What Good Prompts Do

Good prompts:

- name the canonical rigid body or main structure first
- specify 2-4 visual/structural cues that make the category recognizable
- include a few high-value appearance cues such as finish, material, silhouette, or product-grade detailing
- identify the dominant articulation clearly
- keep secondary motions subordinate to the main object
- describe where moving parts are mounted or supported
- imply plausible load paths, hinge placements, and link relationships

Example pattern:

`Model a [canonical object] with [2-4 structural cues]. Include [primary articulation]. Include [secondary articulation] only if it is a standard feature of this object class. Keep [named subassemblies] rigid and prioritize believable proportions and attachment over extra moving parts.`

## What Bad Prompts Do

Bad prompts:

- lead with a list of joints instead of the object itself
- ask for many coequal motions in one prompt
- use optional branching language that expands the search space
- tell the model to keep the body simple while making articulation the main objective
- encourage “mechanical expressiveness” without naming the actual structure that should exist
- add extra articulation just to make the sample seem richer

Problem phrases to avoid unless there is a strong category-specific reason:

- `if needed`
- `if useful`
- `optional`
- `extra articulation`
- `mechanically expressive`
- `one or two`
- `or removable`
- `or rotation`
- `keep the body simple`

These phrases often push the model toward gratuitous joints, underdesigned bodies, and fragile geometry.

## Prompt Style

For `final_10k`, prompts should usually be:

- short enough to read as one coherent object description
- detailed enough to imply finish, materials, and product character
- written as a single high-quality object prompt, not a checklist dump

The best prompts often read like:

- `a realistic office monitor with a matte black housing, a slim center column, and a compact circular base`
- `a turnstile gate with brushed metal arms, a sturdy central column, and a clean transit-station appearance`

Aim for that level of density: visually specific, mechanically grounded, and not verbose.

## Articulation Budget

Each category should have an articulation budget.

Use these defaults unless there is a strong reason not to.

### Form-First Categories

Examples:

- range hoods
- keyboards
- tackle boxes
- microwaves
- pump bottles

Budget:

- 1 dominant articulation
- 0-1 secondary articulation

Prompt strategy:

- lead with shell or body identity
- keep controls, doors, handles, or panels subordinate
- avoid turning every service feature into a separate mechanism

### Hybrid Categories

Examples:

- wheelbarrows
- wagons
- scooters
- hand trucks
- suitcases

Budget:

- 1 dominant articulation
- 1 secondary articulation if canonical
- everything else static unless absolutely central to the category

Prompt strategy:

- lead with the rigid archetype and support structure
- specify the main moving assembly
- allow only one additional motion if it is standard and visually compatible

### Mechanism-First Categories

Examples:

- monitor mounts
- pan-tilt modules
- serial arms
- folding linkage chains

Budget:

- multiple articulations are acceptable

Prompt strategy:

- lead with the joint topology and member structure
- still specify the physical architecture of hubs, links, brackets, rails, or yokes
- do not leave the model to invent the support structure on its own

## Attachment Rule

Prompts should make attachment relationships obvious.

Every moving part should have an implied support:

- doors hang from a frame or carcass
- wheels sit in forks, axles, or side frames
- lids hinge off a body shell
- trays slide on rails or guides
- handles mount to brackets or pivots
- articulated heads sit on yokes, columns, or arm ends

If a moving part does not have a named support in the prompt, the model is more likely to create a visually floating part or a weakly attached joint.

## Visual Coherence Rule

Prompts should describe the object as one coherent assembly, not as a bag of features.

Use wording that ties parts together:

- `single front fork`
- `rigid tray body`
- `straight support handles`
- `box-section links`
- `wall plate with two articulated extension arms`
- `hinged lid integrated into a compact rectangular case`

Prefer this over feature piles like:

- `spinning wheels, folding panel, telescoping handle, extra hinge`

The model needs a structural story, not just a motion checklist.

## No Floating Parts

Because the dataset target is realistic viewer output with no floating-looking parts, prompts should explicitly encourage:

- grounded support members
- visible brackets, forks, yokes, frames, rails, hinges, or hubs
- believable clearances and mounting points
- stable base geometry where appropriate

Useful wording:

- `with visible support brackets`
- `mounted on a rigid frame`
- `carried by a yoke`
- `supported by side rails`
- `hinged from the rear edge of the housing`
- `mounted to a central column`
- `with the wheel captured in a fork`

Avoid prompts that only mention the moving part and not the mount.

## Prompt Shape

Prefer this sentence order:

1. Name the object and its canonical form
2. Add 2-4 structural cues
3. Name the dominant articulation
4. Add at most one secondary articulation if canonical
5. End with a realism constraint

Template:

`Model a [category] with [structural cue 1], [structural cue 2], and [structural cue 3]. Include [primary articulation]. Include [secondary articulation] only if it is a standard feature of this object class. Keep [main body / frame / shell] rigid and prioritize believable proportions, visible support, and attached motion over extra articulated parts.`

## Category-Specific Guidance

### For Vehicle-Like or Rolling Objects

- identify the rigid chassis or body first
- name the wheel support architecture explicitly
- describe the wheel appearance when it matters to realism: tire profile, rim, hub, fork, axle, or spoke structure
- do not ask for every possible deployable subfeature
- avoid combining steering, suspension-like motion, telescoping members, folding supports, and dumping behavior unless the category truly requires all of them

For wheel-like categories, prompts should bias away from placeholder disc wheels.

Prefer wording like:

- `rounded rubber tires`
- `visible rims and hubs`
- `spoked wheels`
- `wheels captured in forks or axle mounts`

Avoid vague wheel wording when realism depends on the wheel form, because the model may collapse the wheel into a flat cylinder stack.

### For Appliances and Enclosures

- lead with the shell, carcass, or housing
- treat doors, lids, knobs, and service panels as secondary
- prefer one main access motion plus one control motion
- do not stack multiple small access features just to increase articulation count

### For Furniture

- decide whether the category is form-first or mechanism-first
- for chairs, stools, and lounge furniture, pick the one or two adjustments that define the object
- avoid prompting independent motion in every subassembly unless it is canonical

### For Tools and Fixtures

- identify the heavy fixed body first
- specify the working motion second
- only add a secondary joint when it directly supports the working mechanism

### For Linkages, Arms, and Mounts

- articulation can lead the prompt
- still specify member types such as plates, box beams, yokes, rails, hubs, and brackets
- make the joint chain legible and compact

## Rewrite Rules

When revising a weak prompt:

1. Remove optional articulation language first.
2. Reduce the prompt to one dominant motion.
3. Add explicit structural cues for the rigid body and supports.
4. Re-add at most one secondary motion if it is standard for the category.
5. End with a realism clause that favors attachment and silhouette over motion count.

## Before / After Examples

### Wheelbarrow

Weaker:

`Model a wheelbarrow with a spinning front wheel, articulated support legs that fold for storage, and a dumping tub hinge if needed to make the object more mechanically expressive. Keep the frame readable and the articulated motions plausible for a utility wheelbarrow.`

Stronger:

`Model a utility wheelbarrow with a rigid tray body, single front fork, side braces, and straight support handles. Include a spinning front wheel. Add a dumping tray hinge only if it can be integrated without weakening the frame or tray structure. Prioritize a believable industrial silhouette, attached supports, and clean proportions over extra moving parts.`

### Open Wagon Cart

Weaker:

`Model an open wagon cart with spinning wheels, a front steering axle linked to a pull handle, and folding side panels if needed for extra articulation. Keep the cart body simple and emphasize the wagon-style steering linkage and rolling hardware.`

Stronger:

`Model an open wagon cart with a rigid rectangular cargo bed, four exposed wheels, a front steering axle, and a pull handle connected to the steering assembly. Include wheel spin and front-axle steering. Keep the side walls rigid unless folding panels are a standard wagon feature for this variant. Prioritize a coherent wagon body and readable steering support geometry.`

### Range Hood

Weaker:

`Model a range hood with hinged or removable filter panels, rotating control knobs or slider switches, and an adjustable vent flap if useful. Keep the hood shell simple and focus on service and control articulation.`

Stronger:

`Model a wall-mounted range hood with a rigid metal canopy, underside filter bay, and a compact front control strip. Include either hinged filter access panels or removable filter cartridges, plus one realistic control mechanism such as rotary knobs or slider switches. Keep the housing dominant and ensure all service parts read as attached to the hood shell.`

## Review Checklist

Before accepting a new category prompt, ask:

- Does the first clause define a recognizable object, not just motions?
- Are the main rigid structures named?
- Does the prompt include enough visual/material fidelity to suggest a high-quality object rather than a schematic mechanism?
- Is there a clear dominant articulation?
- Is every moving part attached to an obvious support in the wording?
- For wheel-like objects, does the prompt discourage flat disc-wheel geometry by naming tires, rims, hubs, forks, or spokes?
- Would removing one secondary articulation improve realism?
- Does the prompt avoid optional branching language?
- Does the prompt bias toward a coherent silhouette instead of feature accumulation?
- Would a model following this prompt be likely to avoid floating-looking parts?

If any answer is `no`, rewrite the prompt before running it.

## Dataset Policy

For `final_10k`, prefer:

- visual coherence over articulation count
- realistic attachment over mechanical novelty
- canonical category identity over feature breadth
- one strong mechanism over several weak ones

The prompt should make the right object easy to generate.
It should not ask the model to invent a richer object by adding more joints.
