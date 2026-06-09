"""Phase 0 evaluator harness: player-less headless throughput measurement.

This is the make-or-break link of the project (see docs/design.md and
docs/specs/2026-06-09-phase0-evaluator-feasibility-design.md). It launches
Factorio headless on a self-contained Lua scenario that materializes a blueprint
via `create_entity`, feeds it, warms it up, and reads throughput from
`force.get_item_production_statistics(surface)`.

Path B (scripted scenario, single run) -- not `--benchmark`.

Isolation (AC4): a dedicated write-data directory under the project holds the
scenario, a generated config, and script-output. The player's ~/.factorio is
never touched.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

# Standalone install on caladan (verified 2026-06-09). Overridable via env for
# other machines / CI.
_DEFAULT_BINARY = Path.home() / "Games" / "factorio" / "bin" / "x64" / "factorio"

# Project-local Factorio data dir holding the scenario (isolated from ~/.factorio).
_PROJECT_DATA = Path(__file__).resolve().parents[2] / "factorio_data"
_SCENARIO_DIR = _PROJECT_DATA / "scenarios" / "phase0-throughput"

# Default tick windows; tuned for <1% reproducibility (AC2). The window is long
# enough that integer-count granularity (+/-1 item) stays well under 1%.
WARMUP_TICKS = 1800  # 30 s of game time to reach steady state
MEASURE_TICKS = 18000  # 300 s of game time -> hundreds of items at the toy rate

# Simulate faster than real time (CPU-bound). Throughput per tick is unchanged.
GAME_SPEED = 64.0


def factorio_binary() -> Path | None:
    """Locate the Factorio binary, or None if absent.

    Resolution order: FACTORIO_BINARY env var, the known standalone path, then
    `factorio` on PATH. Returns None when nothing is found so tests can skip.
    """
    env = os.environ.get("FACTORIO_BINARY")
    if env and Path(env).is_file():
        return Path(env)
    if _DEFAULT_BINARY.is_file():
        return _DEFAULT_BINARY
    found = shutil.which("factorio")
    return Path(found) if found else None


def _read_data_path(binary: Path) -> Path:
    """The install's read-data directory (sibling of bin/)."""
    # binary = <install>/bin/x64/factorio ; data = <install>/data
    return binary.parents[2] / "data"


def _lua_str(s: str) -> str:
    """Encode a Python string as a Lua long-bracket literal (no escaping needed)."""
    # Blueprint strings contain no `]]`, so a simple long bracket is safe.
    return f"[[{s}]]"


def _write_params(
    blueprint_string: str,
    *,
    target_item: str,
    input_item: str,
    warmup_ticks: int,
    measure_ticks: int,
    game_speed: float,
    keep_open: bool,
) -> None:
    params = (
        "return {\n"
        f"  blueprint = {_lua_str(blueprint_string)},\n"
        f"  target_item = {_lua_str(target_item)},\n"
        f"  input_item = {_lua_str(input_item)},\n"
        f"  warmup_ticks = {warmup_ticks},\n"
        f"  measure_ticks = {measure_ticks},\n"
        f"  game_speed = {game_speed},\n"
        f"  keep_open = {'true' if keep_open else 'false'},\n"
        "}\n"
    )
    (_SCENARIO_DIR / "params.lua").write_text(params)


def _write_config(write_data: Path) -> Path:
    config = write_data / "config.ini"
    config.write_text(
        "[path]\n"
        f"read-data={_read_data_path(factorio_binary())}\n"
        f"write-data={write_data}\n"
    )
    return config


def _write_server_settings(write_data: Path) -> Path:
    # A headless server pauses ticks when no player is connected; auto_pause
    # false keeps it running so the scenario actually advances and measures.
    settings = write_data / "server-settings.json"
    settings.write_text(json.dumps({
        "name": "phase0",
        "description": "Phase 0 throughput evaluator (local, not public)",
        "visibility": {"public": False, "lan": False},
        "require_user_verification": False,
        "auto_pause": False,
    }))
    return settings


def measure_throughput(
    blueprint_string: str,
    item: str,
    *,
    input_item: str = "iron-ore",
    warmup_ticks: int = WARMUP_TICKS,
    measure_ticks: int = MEASURE_TICKS,
    game_speed: float = GAME_SPEED,
    headless: bool = True,
) -> float:
    """Materialize a blueprint headless and return the conveyed rate of `item`.

    Measures the rate at which `item` is conveyed into the output (sink) chest --
    a design's real efficiency -- not raw machine production (collected as a
    secondary figure in the result file).

    Args:
        blueprint_string: A Factorio blueprint export string.
        item: The output item prototype name to measure (e.g. "iron-plate").
        input_item: The item the source infinity-chest supplies.
        warmup_ticks: Ticks to run before measuring (reach steady state).
        measure_ticks: Ticks over which to measure the conveyed-count delta.
        game_speed: Simulation speed multiplier (CPU-bound); does not affect the
            measured per-tick throughput, only wall-clock time.
        headless: True runs as a windowless server (the loop's mode); False opens
            the GUI so you can watch the materialization (debug mode). Windowed
            mode ignores game_speed acceleration in practice (GUI-capped).

    Returns:
        Conveyed throughput in items per second over the measurement window.
    """
    binary = factorio_binary()
    if binary is None:
        raise RuntimeError("no Factorio binary found")

    _write_params(
        blueprint_string,
        target_item=item,
        input_item=input_item,
        warmup_ticks=warmup_ticks,
        measure_ticks=measure_ticks,
        game_speed=game_speed if headless else 1.0,
        keep_open=not headless,
    )

    # Isolated write-data: the scenario must be discoverable, so we point
    # write-data at the project data dir (which holds scenarios/).
    write_data = _PROJECT_DATA
    config = _write_config(write_data)
    result_file = write_data / "script-output" / "phase0-result.json"
    if result_file.exists():
        result_file.unlink()

    # Headless uses the windowless server mode; debug mode opens the GUI so the
    # materialization can be watched. Both load the same scenario.
    scenario_flag = "--start-server-load-scenario" if headless else "--load-scenario"
    cmd = [
        str(binary),
        "--config", str(config),
        scenario_flag, "phase0-throughput",
        "--disable-audio",
    ]
    if headless:
        cmd += ["--server-settings", str(_write_server_settings(write_data))]
    # Run in the background and poll for the result file: --until-tick requires
    # --load-game, and Lua has no hard quit, so the scenario writes the result
    # then sets game_finished; we read the file and terminate the process.
    # stdin must stay open: a headless server reads it for admin commands and,
    # given EOF, never advances ticks. We keep the pipe open for the run's life.
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    try:
        result = _poll_for_result(proc, result_file, timeout=300)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    return float(result["rate_per_second"])


def _poll_for_result(proc: subprocess.Popen, result_file: Path, *, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if result_file.exists():
            return json.loads(result_file.read_text())
        if proc.poll() is not None:
            # Process exited before producing the file -> surface its output.
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(
                f"Factorio exited (code {proc.returncode}) without a result file.\n"
                f"output tail:\n{out[-3000:]}"
            )
        time.sleep(0.2)
    raise RuntimeError("timed out waiting for the scenario result file")
