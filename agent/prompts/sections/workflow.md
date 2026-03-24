<workflow>
- Start by reading the bound scaffold/file with the provider's read tool so you are working from the exact current implementation.
- Read the injected SDK docs for exact helper signatures, caveats, and package-specific constraints before inventing an API usage pattern.
- Use `find_examples` for unfamiliar modeling or testing patterns, not as a substitute for API documentation.
- Use `probe_model` before editing when placement, containment, clearance, support, overlap risk, pose behavior, or overall scale/proportion is uncertain, and when the model knows a pair should not overlap.
- Use `probe_model` for debugging and geometry intuition; use `run_tests()` for persistent regression checks that survive across turns.
- If parts may be colliding when they should be separate, or the model knows a specific pair should not overlap, use `pair_report(...)`, `gap_report(...)`, `overlap_report(...)`, `contact_report(...)`, or `find_clearance_risks(...)` before changing geometry or relaxing thresholds.
- If parts may be floating, isolated, weakly mounted, or otherwise unsupported, use `find_floating_parts(...)`, `nearest_neighbors(...)`, `mount_report(...)`, and `within_report(...)` before patching supports or attachments.
- If the object may be the wrong size, too bulky, too thin, unevenly spaced, or compositionally off, use `summary(...)`, `dims(...)`, `projection(...)`, `layout_report(...)`, `grid_report(...)`, or `symmetry_report(...)` to measure the current geometry first.
- If articulation behavior is uncertain, inspect multiple poses with `pose(...)`, `sample_poses(...)`, and pose-aware probe reports before editing joint limits or moving parts.
- Probe first in the same object-first style as `run_tests()`: resolve `part(...)`, `joint(...)`, and `visual(...)` locals once, then pass those objects into probe reports before encoding the discovered invariant in `run_tests()`.
- Make the smallest viable edit that fixes the real issue, but update `run_tests()` in the same edit whenever geometry, motion, or visible structure changes.
- After compile/QC feedback, classify the problem before patching: local bug, wrong representation, wrong composition, or wrong proportions.
- If the same region has already absorbed repeated local nudges for the same issue class, stop tuning and rewrite that region from the intended visual/mechanical behavior.
</workflow>
