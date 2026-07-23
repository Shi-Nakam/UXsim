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

## Scripts

| File | Role |
|------|------|
| `batch_assignment_318_lifecycle_diagnostic.py` | Traces batch ID 318 / veh_1619 / node g_4_1 from assignment through service-unit completion. Confirms service unit 318 was removed normally while assignment 318 remained on the vehicle. |
| `batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py` | 5,000- and 10,000-vehicle comparison: signalized all-red UXsim vs FCFS (clearance=1) vs BATCH (clearance=1). BATCH fails at 5,000 vehicles with a known prefix violation. |
| `batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py` | 5,000-vehicle comparison with clearance=0. Shows prefix violation reproduces without clearance=1 queue retention. |
| `node_revisit_high_demand_5000_diagnostic.py` | Compares Node revisit rates across signalized UXsim, FCFS, and BATCH on the same demand. BATCH stops at W.T=605 with the known prefix violation. |

## Known prefix violations (intentional)

Non-zero exit codes from these scripts may be **expected**:

- **clearance=1 high-demand:** `g_5_4`, inlink `h_5_3_4`, veh_1952 (5,000-vehicle BATCH case)
- **clearance=0 high-demand:** `g_4_1`, inlink `v_5_4_1`, veh_1619 at W.T=605

Do not treat these as regression test failures. Do not suppress or convert them
to exit code 0.

## Key conclusions (summary)

- **Batch ID 318:** Service unit 318 completed and was removed normally.
  Assignment 318 remained on veh_1619 after the first pass through g_4_1.
  On re-approach via a different inlink, prefix validation treated the stale
  assignment as current → prefix violation.
- **Node revisit:** Not BATCH-specific. Signalized UXsim (~42.7%) and FCFS
  (~23.0%) also show many revisits over the full simulation.
- **BATCH-specific issue:** Past visit assignment leaking into the current
  visit (Node-name-keyed state, no visit distinction)—not revisit itself.

## How to run

From the **repository root** (uxsim must be importable, e.g. `pip install -e .`):

```bash
python diagnostics/order_control/batch_assignment_318_lifecycle_diagnostic.py

python diagnostics/order_control/batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py

python diagnostics/order_control/batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py

python diagnostics/order_control/node_revisit_high_demand_5000_diagnostic.py
```

Some runs take several minutes (5,000-vehicle grid). A non-zero exit after
diagnostic output and a known prefix violation message is acceptable.
