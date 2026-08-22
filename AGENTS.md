# ex4pm-plan agent contract

## Remit

ex4pm-plan is a lean, disposable planning/search compute worker for ex4pm. It is derived from Airbus scikit-decide, but it is not the authority/control plane. Preserve upstream algorithm semantics while keeping the worker small enough to schedule freely in cloud compute.

## Boundary

The worker is CONSTRUCT-only. It may admit a planning problem, execute a retained solver, replay/verify the candidate result, and return evidence. It must never acquire cloud credentials, actuate external state, or manufacture an ex4pm BRCE receipt. ex4pm owns routing, selection, authority, budgets, cloud placement, DO, receipts, replay, and standing beyond the planner invocation.

## 80/20 distribution

Default retained native solver families are A*, BFWS, and IW. The maintained Python domain catalog contains only explicit GraphDomain planning. Heavy RL/GPU, RDDL, flight-planning, scheduling/optimization, LP/POMDP, PDDL/PPDDL, tuning, notebook, and broad demonstration stacks are excluded from this fork.

Python multiprocessing is intentionally unsupported. Do not restore pathos, pynng, or dill to fan out planner work; ex4pm and the cloud scheduler own horizontal concurrency.

## Evidence

Use `UNKNOWN | PARTIAL_ALIVE | ALIVE | BLOCKED | BUILD_BROKEN | UNSUPPORTED` and typed `REFUSED`. A solver name in source is not ALIVE. ALIVE for a solve requires exact execution plus replay of the returned plan against the admitted problem.

## Upstream

The fork baseline is `airbus/scikit-decide@138799ba44a9049ee9bb21a937c9ac669f043afd`. Preserve LICENSE/copyright notices and record future upstream rebases explicitly in `UPSTREAM.md`.

## Verification

Run `pytest -q tests/ex4pm_plan`, build the wheel, then execute `ex4pm-plan capabilities` and an exact solve smoke test. Do not expand CI back to upstream's full scientific/RL matrix unless the maintained capability set explicitly expands.
