# ex4pm-plan agent contract

## Remit

ex4pm-plan is a lean, disposable planning/search compute worker for ex4pm. It is derived from Airbus scikit-decide, but it is not the authority/control plane. Preserve upstream algorithm semantics while keeping the default worker small enough to schedule freely in cloud compute.

## Boundary

The worker is CONSTRUCT-only. It may admit a planning problem, execute a retained solver, replay/verify the candidate result, and return evidence. It must never acquire cloud credentials, actuate external state, or manufacture an ex4pm BRCE receipt. ex4pm owns routing, authority, budgets, cloud placement, DO, receipts, replay, and standing beyond the planner invocation.

## 80/20 distribution

Default retained native solver families are A*, BFWS, and IW. Heavy RL/GPU, RDDL, flight-planning, large scheduling/optimization, LP/POMDP, PDDL grounding, hyperparameter-tuning, notebook, and documentation stacks are outside the default distribution. Reintroducing a heavy edge requires an explicit capability/cost case; do not restore umbrella extras.

## Evidence

Use UNKNOWN | PARTIAL_ALIVE | ALIVE | BLOCKED | BUILD_BROKEN | UNSUPPORTED and typed REFUSED. A solver name in source is not ALIVE. ALIVE for a solve requires exact execution plus replay of the returned plan against the admitted problem.

## Upstream

The fork baseline is `airbus/scikit-decide@138799ba44a9049ee9bb21a937c9ac669f043afd`. Preserve LICENSE/copyright notices and record future upstream rebases explicitly.

## Verification

Run the focused worker suite first: `pytest -q tests/ex4pm_plan`. Then build the wheel and execute `ex4pm-plan capabilities` plus a solve smoke test. Do not expand CI back to upstream's full scientific/RL matrix unless the maintained capability set expands.
