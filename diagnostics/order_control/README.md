# Order-control diagnostics (Phase 4-6N)

## Purpose

This directory holds **diagnostic scripts** for Phase 4-6N: reproducing and
investigating BATCH prefix violations and Node revisit behavior under
high-demand conditions. These scripts record **pre–node-revisit-fix** state.

They are **not** part of the normal regression test suite. Do not add them to
automated test discovery (`tests_*.py` at the repository root).

## Formal record

Detailed results, timelines, and design conclusions are in:

`ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md` **§1G**

Phase 4-6U high-demand re-run results are in **§1H.24**.

## Scripts

| File | Role |
|------|------|
| `batch_assignment_318_lifecycle_diagnostic.py` | Traces batch ID 318 / veh_1619 / node g_4_1 from assignment through service-unit completion. Confirms service unit 318 was removed normally while assignment 318 remained on the vehicle. |
| `batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py` | 5,000- and 10,000-vehicle comparison: signalized all-red UXsim vs FCFS (clearance=1) vs BATCH (clearance=1). **Before Phase 4-6S:** BATCH failed at 5,000 vehicles with a known prefix violation. **After Phase 4-6U:** both cases complete with exit code 0 (see below). |
| `batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py` | 5,000-vehicle comparison with clearance=0. **Before Phase 4-6S:** prefix violation at W.T=605. **After Phase 4-6U:** completes with exit code 0 (see below). |
| `node_revisit_high_demand_5000_diagnostic.py` | Compares Node revisit rates across signalized UXsim, FCFS, and BATCH on the same demand. **Before Phase 4-6S:** BATCH stopped at W.T=605 with the known prefix violation. |

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
```

Some runs take several minutes (5,000-vehicle grid; 10,000-vehicle longer).

**After Phase 4-6U:** the two comparison diagnostics above are expected to exit
0. A non-zero exit after diagnostic output may indicate a new issue.

**Before Phase 4-6S:** a non-zero exit after a known prefix violation message
was acceptable for reproduction scripts.
