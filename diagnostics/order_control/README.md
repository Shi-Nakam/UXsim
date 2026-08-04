# Order-control diagnostics (Phase 4-6N / 4-6V / 4-6W / 4-6X)

## Purpose

This directory holds **diagnostic scripts** for order-control investigation.
They are **not** part of the normal regression test suite. Do not add them to
automated test discovery (`tests_*.py` at the repository root).

**Diagnostic categories:**

- **Phase 4-6N legacy (4 scripts):** pre-fix bug reproduction and root-cause investigation
- **Phase 4-6V post-fix (2 scripts):** exploratory manual regression after zero-service reformation fix
- **Phase 4-6W reference model (1 module):** mimic-World Level 2 `t_trigger` reference estimator (not connected to UXsim body). Extended in Phase 4-6X with unarrived service-unit virtual advancement and reference-only BATCH serve.

Modules and scripts under `diagnostics/order_control/` are **not** discovered by repository-root `tests_*.py` automated test discovery.

Phase 4-6W has a **dedicated test at the repository root** (separate from the diagnostic scripts above):

- `tests_order_control_batch_t_trigger_level_2_reference.py`

Phase 4-6X has an additional **dedicated test** at the repository root:

- `tests_order_control_batch_t_trigger_level_2_unarrived_reference.py`

Those files are standalone reference-model tests, not normal diagnostic scripts and not part of the automated regression suite unless run explicitly.

## Formal record

Detailed results, timelines, and design conclusions are in:

- `ORDER_EXCHANGE_PROGRESS.md` — Phase 4-6V (zero-service reformation, equivalence, batch-size exploration, corrected signal baseline); Phase 4-6W (mimic-World Level 2 `t_trigger` reference model); Phase 4-6X (unarrived service-unit support in reference model)
- `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md` — **§1G** (prefix violations), **§1H.24** (Phase 4-6U high-demand), **§1H.25** (zero-service reformation design, corrected signal setting), **§1H.26** (Phase 4-6W reference model), **§1H.27** (Phase 4-6X unarrived vehicles and reference-only serve)

Do not duplicate capacity tables or N=10 vs signal ratio tables here.

## Scripts

| File | Role |
|------|------|
| `batch_assignment_318_lifecycle_diagnostic.py` | Traces batch ID 318 / veh_1619 / node g_4_1 from assignment through service-unit completion. Confirms service unit 318 was removed normally while assignment 318 remained on the vehicle. |
| `batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py` | 5,000- and 10,000-vehicle comparison: signalized all-red UXsim vs FCFS (clearance=1) vs BATCH (clearance=1). **Before Phase 4-6S:** BATCH failed at 5,000 vehicles with a known prefix violation. **After Phase 4-6U:** both cases complete with exit code 0 (see below). |
| `batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py` | 5,000-vehicle comparison with clearance=0. **Before Phase 4-6S:** prefix violation at W.T=605. **After Phase 4-6U:** completes with exit code 0 (see below). |
| `node_revisit_high_demand_5000_diagnostic.py` | Compares Node revisit rates across signalized UXsim, FCFS, and BATCH on the same demand. **Before Phase 4-6S:** BATCH stopped at W.T=605 with the known prefix violation. |
| `grid_n1_fcfs_route_fixed_small_check.py` | 200 vehicles, 6×6 grid, horizontal-first fixed Manhattan route. FCFS clearance=1 vs size-one BATCH Level 1 clearance=1 on identical vehicle plans. Strict aggregate and per-vehicle comparison (state, arrival_time, travel_time, traveled route, `log_t_link`). Fast independent regression without dynamic route choice. **Not** a general proof for all networks/demands. |
| `grid_10000_batch_size_and_signal_timing_preliminary_check.py` | 10,000 vehicles, 6×6 grid, free routing. Exploratory pre–Level 2 diagnostic. Default run: P1–P4. Modes for size-one BATCH vs FCFS, post-fix strict equivalence, N=10 vs N=20 recheck, and legacy pre-fix investigation. **Not** a formal sensitivity analysis. |
| `level2_virtual_world_reference.py` | Phase 4-6W mimic-World Level 2 `t_trigger` reference model, extended in **Phase 4-6X** with unarrived service-unit virtual advancement, Type A / Type B route classification, `acceptable_outlinks` Vehicle ID modulo selection, and reference-only BATCH serve (`_serve_reference_batch_queue`). Builds a local mimic World from a real snapshot, rebuilds the service queue plus a trigger-only pseudo unit, runs the virtual loop, and returns `t_virtual_trigger` / `t_level_2_candidate` plus `virtual_node_arrival_timesteps`, `virtual_outlink_choices`, and `service_stop_trace`. **Not** the body Level 2 implementation; **not** connected to `form_order_control_batch()`. Does not modify the real World. Performance benchmark not run. |

## Phase 4-6W / 4-6X reference model (`level2_virtual_world_reference.py`)

**Role:** diagnostic / design baseline for Level 2 semantics before body connection.

**Phase 4-6W (baseline):**

- Builds a local mimic World from a real World snapshot at W.T
- Rebuilds existing service units and appends a trigger-only pseudo service unit (trigger is **not** formally batched in the real World)
- Fixes `route_next_link` at the snapshot value
- Copies capacity and clearance state; refills capacity only from virtual offset ≥ 1
- Replicates outlink vehicles and advances them with standard car-following; uses standard sink `end_trip()`
- Returns the trigger’s virtual pass timestep (`t_virtual_trigger`) and a provisional candidate `max(t_level_1, t_virtual_trigger)` when resolved
- Excludes unassigned vehicles behind the trigger from the mimic World

**Phase 4-6X (extension, reference model only — body not connected):**

- Unarrived service-unit Vehicle virtual advancement on mimic inlinks and virtual node-arrival registration (`virtual_node_arrival_timesteps`)
- Reference-only BATCH serve (not `uxsim.py` body serve): Type A fixed outlink vs Type B optimistic virtual outlink choice at transfer time
- `acceptable_outlinks` built per vehicle evaluation; Type B uses Vehicle ID modulo selection on sorted acceptable outlinks (not full-outlink cyclic search). Does not guarantee optimal load balancing
- `service_stop_trace` with `stop_reason` (direct end reason), `blocked_inlinks`, `skipped_units`, `active_inlink` rules
- `virtual_outlink_choices` for Type B selections

**Dedicated tests (repository root, not under `diagnostics/`):**

Phase 4-6W regression (18 tests; file unchanged):

```bash
python tests_order_control_batch_t_trigger_level_2_reference.py
```

Phase 4-6X unarrived / reference-only serve (28 tests):

```bash
python tests_order_control_batch_t_trigger_level_2_unarrived_reference.py
```

Full design, implementation record, test matrix, and open issues: `ORDER_EXCHANGE_PROGRESS.md` (Phase 4-6W, Phase 4-6X) and design notes **§1H.26**, **§1H.27**. Do not treat this module as “Level 2 complete” or as enabled in the UXsim body. Performance benchmark not run.

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

- `signal=[59,0,59,0]` — effective 60/1/60/1 transfer timesteps under current UXsim discrete implementation
- Same cycle-length-based offset formula as before; offset values 0.0 / 29.5 / 59.0 / 88.5
- Runs only the corrected-signal 10,000-vehicle case (`S_CORRECTED_SIGNAL_EFFECTIVE_60_1_60_1`)
- Does **not** run FCFS, BATCH, or P1–P4
- Includes real-Node timing sanity check and vehicle plan invariant check
- Full results: `ORDER_EXCHANGE_PROGRESS.md` and design notes **§1H.25**

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

See **Phase 4-6V scripts** above for `grid_10000_batch_size_and_signal_timing_preliminary_check.py` CLI modes.

Some runs take several minutes (5,000-vehicle grid; 10,000-vehicle longer).

**After Phase 4-6U:** the two comparison diagnostics above are expected to exit
0. A non-zero exit after diagnostic output may indicate a new issue.

**Before Phase 4-6S:** a non-zero exit after a known prefix violation message
was acceptable for reproduction scripts.
