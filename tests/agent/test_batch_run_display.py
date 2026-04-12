from __future__ import annotations

from io import StringIO

from rich.console import Console

from agent.tui.batch_run import BatchRunDisplay


def _make_display() -> tuple[BatchRunDisplay, StringIO]:
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None, width=180)
    display = BatchRunDisplay(
        console=console,
        experiment_name="hinge_batch",
        total_runs=20,
        concurrency=4,
        model_id="gpt-5.4",
        enabled=True,
    )
    return display, buffer


def test_add_compaction_event_shows_row_label_and_cost() -> None:
    display, buffer = _make_display()
    display.add_run("rec_hinge_0001", "make a hinge")

    display.add_compaction_event(
        "rec_hinge_0001",
        trigger="compile_plateau",
        estimated_saved_next_input_tokens=90_000,
        billed_cost=0.00045,
        previous_response_id_cleared=True,
    )

    output = buffer.getvalue()
    assert "compact [#001/20] rec_hinge_0001" in output
    assert "compile plateau" in output
    assert "saved≈90.0K" in output
    assert "billed=$0.000450" in output
    assert "prev=cleared" in output


def test_add_maintenance_event_shows_cache_lifecycle_line() -> None:
    display, buffer = _make_display()
    display.add_run("rec_hinge_0001", "make a hinge")

    display.add_maintenance_event(
        "rec_hinge_0001",
        {"kind": "cache_create", "cache_name": "cachedContents/cache_1"},
        billed_cost=0.0,
    )

    output = buffer.getvalue()
    assert "maint   [#001/20] rec_hinge_0001" in output
    assert "cache create" in output
    assert "cachedContents/cache_1" in output
