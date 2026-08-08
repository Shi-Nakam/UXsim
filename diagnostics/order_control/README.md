# Order-control diagnostics (Phase 4-6N / 4-6V / 4-6W / 4-6X / 4-6Y)

## Purpose

This directory holds **diagnostic scripts** for order-control investigation.
They are **not** part of the normal regression test suite. Do not add them to
automated test discovery (`tests_*.py` at the repository root).

**Diagnostic categories:**

- **Phase 4-6N legacy (4 scripts):** pre-fix bug reproduction and root-cause investigation
- **Phase 4-6V post-fix (2 scripts):** exploratory manual regression after zero-service reformation fix
- **Phase 4-6W reference model (1 module):** mimic-World Level 2 `t_trigger` reference estimator.
- **Phase 4-6X reference-model extension:** unarrived service-unit Vehicle advancement, route-state classification, and reference-only BATCH service processing before body connection.
- **Phase 4-6Y body connection and diagnostics (2 scripts):** Level 2 body connection (`6e6a601`, §1H.27.42), unarrived route-state fix and Level 1 vs Level 2 grid diagnostic (`af0e037`, §1H.27.43), and N=1 BATCH Level 2 vs FCFS diagnostic with mimic-World Analyzer performance fix (§1H.27.44). The two diagnostic scripts are manual diagnostics, not automated regression tests. (The count “2 scripts” is the number of Phase 4-6Y diagnostic scripts, not the total number of Phase 4-6Y changed files.)

Modules and scripts under `diagnostics/order_control/` are **not** discovered by repository-root `tests_*.py` automated test discovery.

**Dedicated tests at the repository root** (separate from diagnostic scripts):

- `tests_order_control_batch_t_trigger_level_2_reference.py` — **20 tests**
- `tests_order_control_batch_t_trigger_level_2_unarrived_reference.py` — **29 tests**
- `tests_order_control_batch_t_trigger_level_2_body.py` — **22 tests** (Level 2 body connection)

Those files are standalone tests, not normal diagnostic scripts and not part of the automated regression suite unless run explicitly.

## Formal record

Detailed results, timelines, and design conclusions are in:

- `ORDER_EXCHANGE_PROGRESS.md` — Phase 4-6V (zero-service reformation, equivalence, batch-size exploration, corrected signal baseline); Phase 4-6W (mimic-World Level 2 `t_trigger` reference model); Phase 4-6X (unarrived service-unit support in reference model); **Phase 4-6Y** (Level 2 body connection, grid diagnostics, N=1 equivalence, mimic-World performance fix, 5,000/10,000-vehicle additional validation)
- `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md` — **§1G** (prefix violations), **§1H.24** (Phase 4-6U high-demand), **§1H.25** (zero-service reformation design, corrected signal setting), **§1H.26** (Phase 4-6W reference model), **§1H.27** (Phase 4-6X reference-model extension), **§1H.27.42** (Phase 4-6Y: Level 2 body connection), **§1H.27.43** (Phase 4-6Y: unarrived route-state fix, 5,000-vehicle Level 1 vs Level 2), **§1H.27.44** (Phase 4-6Y: N=1 BATCH Level 2 vs FCFS, mimic-World Analyzer skip), **§1H.27.45** (Phase 4-6Y: BATCH-related comparisons across levels, horizons, signalized UXsim, and FCFS at 5,000 and 10,000 vehicles)

Do not duplicate capacity tables or N=10 vs signal ratio tables here.

## Scripts

| File | Role |
|------|------|
| `batch_assignment_318_lifecycle_diagnostic.py` | Traces batch ID 318 / veh_1619 / node g_4_1 from assignment through service-unit completion. Confirms service unit 318 was removed normally while assignment 318 remained on the vehicle. |
| `batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py` | 5,000- and 10,000-vehicle comparison: signalized all-red UXsim vs FCFS (clearance=1) vs BATCH (clearance=1). **Before Phase 4-6S:** BATCH failed at 5,000 vehicles with a known prefix violation. **After Phase 4-6U:** both cases complete with exit code 0 (see below). |
| `batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py` | 5,000-vehicle comparison with clearance=0. **Before Phase 4-6S:** prefix violation at W.T=605. **After Phase 4-6U:** completes with exit code 0 (see below). |
| `node_revisit_high_demand_5000_diagnostic.py` | Compares Node revisit rates across signalized UXsim, FCFS, and BATCH on the same demand. **Before Phase 4-6S:** BATCH stopped at W.T=605 with the known prefix violation. |
| `grid_n1_fcfs_route_fixed_small_check.py` | 200 vehicles, 6×6 grid, horizontal-first fixed Manhattan route. FCFS clearance=1 vs size-one BATCH Level 1 clearance=1 on identical vehicle plans. Strict aggregate and per-vehicle comparison (state, arrival_time, travel_time, traveled route, `log_t_link`). Fast independent regression without dynamic route choice. **Not** a general proof for all networks/demands. |
| `grid_10000_batch_size_and_signal_timing_preliminary_check.py` | 10,000 vehicles, 6×6 grid, free routing. Exploratory pre–Level 2 diagnostic. Default run: P1–P4. Modes for size-one BATCH vs FCFS, post-fix strict equivalence, N=10 vs N=20 recheck, and legacy pre-fix investigation. **Not** a formal sensitivity analysis. Accepts `--corrected-signal-baseline-only --num-vehicles 5000`. 5,000-vehicle corrected-signal baseline completed. On 5,000-vehicle runs, cross-scale differences, ratios, and rankings vs 10,000-vehicle historical references are skipped. Details: **§1H.27.45**. |
| `grid_level_1_vs_level_2_check.py` | **Phase 4-6Y** (`af0e037`, §1H.27.43, §1H.27.45). Accepts `--virtual-horizon` (default 30). 5,000- and 10,000-vehicle grid network diagnostic. N=10, Level 1 vs Level 2, traffic results, Level 2 counters, timing. **5,000 and 10,000 vehicles: Level 1 vs Level 2 with h=30 and h=50 completed.** |
| `grid_n1_level_2_vs_fcfs_check.py` | **Phase 4-6Y** (`5439cf3`, §1H.27.44, §1H.27.45). 200 / 1,000 / 5,000 / 10,000 vehicles. N=1 BATCH Level 2 vs FCFS, strict aggregate and per-vehicle comparison, Level 2 counters. **200 / 1,000 / 5,000 / 10,000 vehicles: `exact_match` confirmed.** Not a general theoretical proof. |
| `level2_virtual_world_reference.py` | **Phase 4-6W / 4-6X reference model** — pre-body-connection design baseline. Body implementation is in `uxsim/order_control_batch_level_2_reference.py` (body connection: **Phase 4-6Y**, `6e6a601`, §1H.27.42). Mimic-World Analyzer skip applies to the body path (Phase 4-6Y, §1H.27.44). |

## Phase 4-6Y: Level 2 body connection and grid diagnostics

**Level 2 body connection (`6e6a601`, §1H.27.42):** Level 2 body connection, Level 1 fallback on unresolved, 4 lightweight counters, virtual horizon setting.

**Unarrived route-state fix and Level 1 vs Level 2 diagnostic (`af0e037`, §1H.27.43):** Unarrived Vehicle route-state fix; `grid_level_1_vs_level_2_check.py`; 5,000- and 10,000-vehicle Level 1 vs Level 2 comparison completed (h=30 and h=50). Details: **§1H.27.45**.

**N=1 equivalence and Analyzer skip (§1H.27.44):** N=1 BATCH Level 2 vs FCFS diagnostic (`grid_n1_level_2_vs_fcfs_check.py`); mimic-World Analyzer skip (`639444f`); 200 / 1,000 / 5,000 / 10,000 vehicles `exact_match`. Details: **§1H.27.44**, **§1H.27.45**.

**5,000/10,000-vehicle additional validation (§1H.27.45):** virtual horizon 30 vs 50 comparison; corrected-signalized UXsim at 5,000 vehicles; FCFS and BATCH relative positioning. virtual horizon 30 retained as provisional (not a formal or optimal value). horizon 50 improved resolved rate but increased travel time, distance, last completion time, and exec time at both scales.

Before mimic-World Analyzer skip, the 5,000-vehicle N=1-L2 case did not complete within 20+ hours (user interrupted). After `create_analyzer=False` for mimic Worlds only, the same 5,000-vehicle case completed in about 12 min 46 s (765.662 s N1-L2 exec). Full numbers: `ORDER_EXCHANGE_PROGRESS.md` (Phase 4-6Y) and design notes **§1H.27.42〜§1H.27.45**.

## Phase 4-6W / 4-6X reference model (`level2_virtual_world_reference.py`)

**Role:** diagnostic / design baseline for Level 2 semantics. The UXsim **body** now uses `uxsim/order_control_batch_level_2_reference.py` (§1H.27.42). This file documents the pre-connection reference model.

**Phase 4-6W (baseline):**

- Builds a local mimic World from a real World snapshot at W.T
- Rebuilds existing service units and appends a trigger-only pseudo service unit (trigger is **not** formally batched in the real World)
- Fixes `route_next_link` at the snapshot value
- Copies capacity and clearance state; refills capacity only from virtual offset ≥ 1
- Replicates outlink vehicles and advances them with standard car-following; uses standard sink `end_trip()`
- Returns the trigger’s virtual pass timestep (`t_virtual_trigger`) and a provisional candidate `max(t_level_1, t_virtual_trigger)` when resolved
- Excludes unassigned vehicles behind the trigger from the mimic World

**Phase 4-6X (extension, reference model — historical record at reference-model stage):**

- Unarrived service-unit Vehicle virtual advancement on mimic inlinks and virtual node-arrival registration (`virtual_node_arrival_timesteps`)
- Reference-only BATCH serve (not `uxsim.py` body serve): Type A fixed outlink vs Type B optimistic virtual outlink choice at transfer time
- `acceptable_outlinks` built per vehicle evaluation; Type B uses Vehicle ID modulo selection on sorted acceptable outlinks (not full-outlink cyclic search). Does not guarantee optimal load balancing
- `service_stop_trace` with `stop_reason` (direct end reason), `blocked_inlinks`, `skipped_units`, `active_inlink` rules
- `virtual_outlink_choices` for Type B selections

**Dedicated tests (repository root, not under `diagnostics/`):**

Phase 4-6W / body reference regression (**20 tests**):

```bash
python tests_order_control_batch_t_trigger_level_2_reference.py
```

Phase 4-6X unarrived / reference-only serve (**29 tests**):

```bash
python tests_order_control_batch_t_trigger_level_2_unarrived_reference.py
```

Level 2 body connection (**22 tests**):

```bash
python tests_order_control_batch_t_trigger_level_2_body.py
```

Full design, implementation record, test matrix, and open issues: `ORDER_EXCHANGE_PROGRESS.md` (Phase 4-6W, Phase 4-6X, **Phase 4-6Y**) and design notes **§1H.26**, **§1H.27**, **§1H.27.42**, **§1H.27.44**, **§1H.27.45**.

## Phase 4-6V scripts (zero-service reformation)

### `grid_n1_fcfs_route_fixed_small_check.py`

- 200 vehicles, 6×6 grid, horizontal-first fixed Manhattan route
- FCFS clearance=1 vs size-one BATCH Level 1 clearance=1, same vehicle plans
- Strict aggregate and per-vehicle checks (state, arrival_time, travel_time, traveled route, `log_t_link`)
- Excludes dynamic route-choice effects for a fast independent regression check
- Not a general theoretical proof for all networks/demands

```bash
python diagnostics/order_control/grid_n1_fcfs_route_fixed_small_check.py
```

### `grid_10000_batch_size_and_signal_timing_preliminary_check.py`

Default (P1–P4):

```bash
python diagnostics/order_control/grid_10000_batch_size_and_signal_timing_preliminary_check.py
```

Lightweight size-one BATCH vs FCFS check:

```bash
python diagnostics/order_control/grid_10000_batch_size_and_signal_timing_preliminary_check.py \
  --n1-equivalence-only
```

Post-fix strict size-one BATCH vs FCFS equivalence:

```bash
python diagnostics/order_control/grid_10000_batch_size_and_signal_timing_preliminary_check.py \
  --n1-equivalence-after-reformation-fix-only
```

Post-fix N=10 vs N=20 recheck:

```bash
python diagnostics/order_control/grid_10000_batch_size_and_signal_timing_preliminary_check.py \
  --batch-size-recheck-after-zero-service-fix-only
```

Corrected signal baseline only (exploratory diagnostic; **not** a formal signal timing sensitivity analysis):

```bash
python diagnostics/order_control/grid_10000_batch_size_and_signal_timing_preliminary_check.py \
  --corrected-signal-baseline-only
```

5,000-vehicle corrected signal baseline (cross-scale historical reference comparison skipped):

```bash
python diagnostics/order_control/grid_10000_batch_size_and_signal_timing_preliminary_check.py \
  --corrected-signal-baseline-only \
  --num-vehicles 5000
```

- `signal=[59,0,59,0]` — effective 60/1/60/1 transfer timesteps under current UXsim discrete implementation
- Same cycle-length-based offset formula as before; offset values 0.0 / 29.5 / 59.0 / 88.5
- Default and other modes remain 10,000-vehicle centered; `--num-vehicles 5000` is accepted only with `--corrected-signal-baseline-only`
- Does **not** run FCFS, BATCH, or P1–P4
- Includes real-Node timing sanity check and vehicle plan invariant check
- Full results: `ORDER_EXCHANGE_PROGRESS.md` and design notes **§1H.25**, **§1H.27.45**

**Default P1–P4 (old signal builder):**

- Uses `signal=[60,1,60,1]` with all-red setting value 1
- Under current discrete implementation, setting value 1 acts as **2 transfer timesteps** (effective [61,2,61,2])
- P2–P4 are **historical exploratory results** from pre-correction conditions
- Do **not** use for current fair signal timing sensitivity analysis; corrected P2–P4 not yet run
- Whether to run corrected-signal P2–P4 later (before Level 2, after Level 2, or not at all) is undecided

**Legacy pre-fix modes** (commit `2b10b08` and earlier bug investigation only; do not use as normal regression on current code):

```bash
python diagnostics/order_control/grid_10000_batch_size_and_signal_timing_preliminary_check.py \
  --n1-first-link-difference-only

python diagnostics/order_control/grid_10000_batch_size_and_signal_timing_preliminary_check.py \
  --n1-first-local-difference-only
```

Legacy modes reproduce the pre-fix mismatch only when checked out at a pre-fix commit. On current post-fix code they do not match old expectations and are not for routine regression.

## Known prefix violations (historical — Phase 4-6N, before Phase 4-6S)

Before Phase 4-6S (current-visit assignment), non-zero exit codes from these
scripts were **expected** when reproducing the pre-fix state:

- **clearance=1 high-demand:** `g_5_4`, inlink `h_5_3_4`, veh_1952 (5,000-vehicle BATCH case). BATCH stopped; 10,000-vehicle case was not reached.
- **clearance=0 high-demand:** `g_4_1`, inlink `v_5_4_1`, veh_1619 at W.T=605

Do not treat those historical non-zero exits as regression test failures. These
historical non-zero results are preserved here as the Phase 4-6N record; they do
not describe the current expected result of the two comparison diagnostics.

The current expected result of the two comparison diagnostics is exit code 0,
as confirmed in Phase 4-6U.

Lifecycle and node-revisit diagnostics also exited with non-zero when BATCH hit
the known prefix violation (Phase 4-6N). They were **not re-run in Phase 4-6U**;
their current exit result was **not confirmed** in this phase.

## Phase 4-6U re-run (after Phase 4-6S / 4-6T)

After Phase 4-6S (current-visit BATCH assignment) and Phase 4-6T (small-scale
revisit end-to-end integration), Phase 4-6U re-ran the high-demand comparison
diagnostics:

| Case | Script | Result |
|------|--------|--------|
| U1 (5,000, clearance=0) | `batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py` | exit 0; all 5,000 vehicles completed; no prefix violation |
| U2 (5,000, clearance=1) | `batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py` | exit 0; all 5,000 vehicles completed; no prefix violation |
| U3 (10,000, clearance=1) | same as U2 (second case in script) | exit 0; all 10,000 vehicles completed; no prefix violation; first time 10,000-vehicle BATCH reached result output |

**Current expectation for the two comparison diagnostics above:** exit code 0
when run on the current codebase (Phase 4-6S assignment fix in place), as
confirmed in Phase 4-6U (U1–U3).

**Not re-run in Phase 4-6U** (not needed; U1–U3 all passed). Current exit
result **not confirmed** in Phase 4-6U:

- `batch_assignment_318_lifecycle_diagnostic.py`
- `node_revisit_high_demand_5000_diagnostic.py`

Diagnostic Python files were **not** modified. Historical non-zero exits above
remain part of the Phase 4-6N record.

Full numbers and conditions: design notes **§1H.24**.

## Key conclusions (summary)

- **Batch ID 318:** Service unit 318 completed and was removed normally.
  Assignment 318 remained on veh_1619 after the first pass through g_4_1.
  On re-approach via a different inlink, prefix validation treated the stale
  assignment as current → prefix violation (pre–Phase 4-6S).
- **Node revisit:** Not BATCH-specific. Signalized UXsim (~42.7%) and FCFS
  (~23.0%) also show many revisits over the full simulation.
- **BATCH-specific issue (fixed in Phase 4-6S):** Past visit assignment leaking
  into the current visit (Node-name-keyed state, no visit distinction)—not
  revisit itself.
- **Phase 4-6Y Level 2 body and diagnostics:** The Level 2 body was connected in commit `6e6a601` (§1H.27.42). The unarrived route-state fix and 5,000/10,000-vehicle Level 1 vs Level 2 diagnostics are recorded in §1H.27.43 and §1H.27.45. The 200 / 1,000 / 5,000 / 10,000-vehicle N=1 BATCH Level 2 vs FCFS diagnostics produced `exact_match` after the mimic-World Analyzer performance fix (§1H.27.44, §1H.27.45). virtual horizon 30 is retained provisionally; horizon 50 improved resolved rate but increased travel time, distance, last completion time, and exec time at both 5,000 and 10,000 vehicles.

## How to run

From the **repository root** (uxsim must be importable, e.g. `pip install -e .`):

```bash
python diagnostics/order_control/batch_assignment_318_lifecycle_diagnostic.py

python diagnostics/order_control/batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py

python diagnostics/order_control/batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py

python diagnostics/order_control/node_revisit_high_demand_5000_diagnostic.py

python diagnostics/order_control/grid_n1_fcfs_route_fixed_small_check.py

python diagnostics/order_control/grid_10000_batch_size_and_signal_timing_preliminary_check.py
```

**Phase 4-6Y — Level 2 body grid diagnostics** (manual; not automated regression):

- `grid_level_1_vs_level_2_check.py`: Level 1 vs Level 2 and virtual-horizon diagnostics
- `grid_n1_level_2_vs_fcfs_check.py`: N=1 BATCH Level 2 vs FCFS equivalence diagnostic

```bash
python diagnostics/order_control/grid_level_1_vs_level_2_check.py --num-vehicles 5000 --virtual-horizon 30

python diagnostics/order_control/grid_level_1_vs_level_2_check.py --num-vehicles 5000 --virtual-horizon 50

python diagnostics/order_control/grid_level_1_vs_level_2_check.py --num-vehicles 10000 --virtual-horizon 30

python diagnostics/order_control/grid_level_1_vs_level_2_check.py --num-vehicles 10000 --virtual-horizon 50

python diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py --num-vehicles 200

python diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py --num-vehicles 1000

python diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py --num-vehicles 5000

python diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py --num-vehicles 10000
```

**Execution status:** 5,000- and 10,000-vehicle Level 1 vs Level 2 (h=30 and h=50) — **completed** (§1H.27.45). 200 / 1,000 / 5,000 / 10,000-vehicle N=1 BATCH Level 2 vs FCFS — **completed** with `exact_match` (§1H.27.44, §1H.27.45). 5,000-vehicle corrected-signalized UXsim baseline — **completed** (§1H.27.45).

See **Phase 4-6V scripts** above for `grid_10000_batch_size_and_signal_timing_preliminary_check.py` CLI modes.

Some runs take several minutes (5,000-vehicle grid; 10,000-vehicle longer).

**After Phase 4-6U:** the two comparison diagnostics above are expected to exit
0. A non-zero exit after diagnostic output may indicate a new issue.

**Before Phase 4-6S:** a non-zero exit after a known prefix violation message
was acceptable for reproduction scripts.
