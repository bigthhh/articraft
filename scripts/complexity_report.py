"""Complexity metrics for generated records — the zero-API-cost seed of an eval harness.

Executes each record's `model.py` to read the real ArticulatedObject and reports
part / joint / geometry metrics, so prompt, SDK, or model changes can be compared
against a baseline instead of judged by eye.

Usage: uv run python scripts/complexity_report.py [data-root]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_BASIC = ("box", "cylinder", "sphere", "cone", "capsule", "torus", "dome")


def _classify(geometry: object) -> str:
    name = type(geometry).__name__.lower()
    if "mesh" in name:
        return "mesh"
    if any(token in name for token in _BASIC):
        return "basic"
    return "advanced"


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _find_cost(obj: object) -> float | None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if "cost" in key.lower() and isinstance(value, (int, float)):
                return float(value)
        for value in obj.values():
            found = _find_cost(value)
            if found is not None:
                return found
    return None


def _dynamic_metrics(model_py: Path) -> dict:
    namespace: dict = {"__file__": str(model_py)}
    code = model_py.read_text(encoding="utf-8")
    exec(compile(code, str(model_py), "exec"), namespace)  # noqa: S102 - trusted local records
    model = namespace.get("object_model")
    if model is None and callable(namespace.get("build_object_model")):
        model = namespace["build_object_model"]()
    if model is None:
        raise ValueError("no object_model produced")

    visuals = [visual for part in model.parts for visual in part.visuals]
    geom_mix = Counter(_classify(visual.geometry) for visual in visuals)
    joint_types = Counter(
        str(getattr(a, "articulation_type", "?")).split(".")[-1] for a in model.articulations
    )
    return {
        "parts": len(model.parts),
        "joints": len(model.articulations),
        "joint_types": dict(joint_types),
        "joint_type_diversity": len(joint_types),
        "visuals": len(visuals),
        "geom_basic": geom_mix.get("basic", 0),
        "geom_advanced": geom_mix.get("advanced", 0),
        "geom_mesh": geom_mix.get("mesh", 0),
        "uses_cadquery": bool(re.search(r"\bimport cadquery\b|mesh_from_cadquery", code)),
        "lines": code.count("\n") + 1,
        "loaded": True,
    }


def _static_fallback(model_py: Path) -> dict:
    code = model_py.read_text(encoding="utf-8")
    return {
        "parts": len(re.findall(r"\.part\(", code)),
        "joints": len(re.findall(r"\.articulation\(|\.articulate\(", code)),
        "joint_types": {},
        "joint_type_diversity": 0,
        "visuals": len(re.findall(r"\.visual\(", code)),
        "geom_basic": 0,
        "geom_advanced": 0,
        "geom_mesh": len(re.findall(r"mesh_from_cadquery", code)),
        "uses_cadquery": bool(re.search(r"\bimport cadquery\b|mesh_from_cadquery", code)),
        "lines": code.count("\n") + 1,
        "loaded": False,
    }


def analyze_revision(model_py: Path) -> dict:
    revision_dir = model_py.parent
    provenance = _read_json(revision_dir / "provenance.json")
    run_summary = provenance.get("run_summary", {})
    generation = provenance.get("generation", {})
    try:
        metrics = _dynamic_metrics(model_py)
    except Exception as exc:  # noqa: BLE001 - report, do not abort the batch
        metrics = _static_fallback(model_py)
        metrics["error"] = f"{type(exc).__name__}: {exc}"
    metrics.update(
        record=model_py.parents[2].name,
        model=generation.get("model_id"),
        turns=run_summary.get("turn_count"),
        status=run_summary.get("final_status"),
        cost=_find_cost(_read_json(revision_dir / "cost.json")),
    )
    return metrics


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return "-" if value is None else str(value)


_SUMMARY_LABELS = {
    "parts_mean": "parts (mean)",
    "joints_mean": "joints (mean)",
    "jtype_diversity_mean": "joint-type diversity",
    "turns_mean": "turns (mean)",
    "cadquery_adoption": "cadquery adoption",
    "basic_geom_ratio": "basic-primitive ratio",
}


def summarize(rows: list[dict]) -> dict:
    loaded = [r for r in rows if r.get("loaded")]
    basis = loaded or rows
    total_geom = sum(r["geom_basic"] + r["geom_advanced"] + r["geom_mesh"] for r in loaded)
    turns = [r["turns"] for r in rows if isinstance(r.get("turns"), int)]
    return {
        "records": len(rows),
        "loaded": len(loaded),
        "parts_mean": mean(r["parts"] for r in basis),
        "joints_mean": mean(r["joints"] for r in basis),
        "jtype_diversity_mean": mean(r["joint_type_diversity"] for r in basis),
        "turns_mean": mean(turns) if turns else None,
        "cadquery_adoption": sum(1 for r in rows if r.get("uses_cadquery")) / len(rows),
        "basic_geom_ratio": (sum(r["geom_basic"] for r in loaded) / total_geom)
        if total_geom
        else None,
    }


def _print_table(rows: list[dict]) -> None:
    header = (
        "model",
        "turns",
        "parts",
        "joints",
        "jtypes",
        "basic",
        "adv",
        "mesh",
        "cadq",
        "lines",
    )
    widths = (22, 5, 5, 6, 6, 5, 3, 4, 4, 5)
    print("  ".join(h.ljust(w) for h, w in zip(header, widths)))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        cells = (
            str(row.get("model"))[:22],
            _fmt(row.get("turns")),
            _fmt(row.get("parts")),
            _fmt(row.get("joints")),
            _fmt(row.get("joint_type_diversity")),
            _fmt(row.get("geom_basic")),
            _fmt(row.get("geom_advanced")),
            _fmt(row.get("geom_mesh")),
            "yes" if row.get("uses_cadquery") else "no",
            _fmt(row.get("lines")),
        )
        print("  ".join(str(c).ljust(w) for c, w in zip(cells, widths)))
        if row.get("error"):
            print(f"    ! static fallback ({row['error']})")


def _print_summary(summary: dict) -> None:
    print(f"\nSummary  ({summary['records']} records, {summary['loaded']} loaded)")
    for key, label in _SUMMARY_LABELS.items():
        value = summary.get(key)
        if value is not None:
            print(f"  {label:<24} {value:.3f}")


def _print_delta(baseline: dict, current: dict) -> None:
    print(f"\nA/B delta   {'metric':<24} {'baseline':>10} {'current':>10} {'delta':>10}")
    for key, label in _SUMMARY_LABELS.items():
        base, cur = baseline.get(key), current.get(key)
        if base is None or cur is None:
            continue
        print(f"            {label:<24} {base:>10.3f} {cur:>10.3f} {cur - base:>+10.3f}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("data_root", nargs="?", default=str(REPO_ROOT / "data"))
    parser.add_argument(
        "--json", dest="json_out", help="write metrics+summary JSON as a reusable baseline"
    )
    parser.add_argument("--compare", dest="baseline", help="baseline JSON to diff this run against")
    args = parser.parse_args(argv)

    data_root = Path(args.data_root)
    model_files = sorted((data_root / "records").glob("*/revisions/*/model.py"))
    if not model_files:
        print(f"No records found under {data_root / 'records'}")
        return 1

    rows = [analyze_revision(path) for path in model_files]
    summary = summarize(rows)
    _print_table(rows)
    _print_summary(summary)

    if args.baseline:
        baseline = _read_json(Path(args.baseline))
        _print_delta(baseline.get("summary", baseline), summary)
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8"
        )
        print(f"\nWrote baseline -> {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
