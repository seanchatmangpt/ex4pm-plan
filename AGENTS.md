# ex4pm-plan agent contract

## Remit

ex4pm-plan is a lean, disposable planning/search compute worker for ex4pm. It is derived from Airbus scikit-decide, but it is not the authority/control plane. Preserve upstream algorithm semantics while keeping the worker small enough to schedule freely in cloud compute.

## Boundary

The worker is CONSTRUCT-only. It may admit a planning problem, execute a retained solver, replay/verify the candidate result, and return evidence. It must never acquire cloud credentials, actuate external state, or manufacture an ex4pm BRCE receipt. ex4pm owns routing, selection, authority, budgets, cloud placement, DO, receipts, replay, and standing beyond the planner invocation.

A ggen generation receipt proves the bounded manufacture of repository artifacts only. It does not upgrade a generated artifact, planner candidate, or worker process into DO authority.

## Manufacturing source

The canonical worker-contract source is `ggen/packs/ex4pm-plan-contract-pack/ontology.ttl`. It reuses PROV-O, DCTERMS, and SKOS for provenance, identity, and capability concepts. `ggen.toml` admits the local pack, and its SPARQL/Tera template projects the graph into `src/ex4pm_plan/generated_contract.py`.

`src/ex4pm_plan/generated_contract.py` is a generated consequence, not an editing surface. Change protocol identity, problem type, exposed solvers, operations, authority, or actuation in the ontology/template and regenerate with `ggen sync run`; do not patch the generated Python by hand. `scripts/verify_ggen_projection.py` is an independent admission court that refuses RDF/projection drift.

Preserve the correspondence:

```text
RDF ontology -> SPARQL bindings -> ggen render/write -> generated contract
             -> worker runtime -> planner execution -> replay evidence
```

Do not collapse the ggen receipt into planner replay evidence or an ex4pm BRCE receipt; they certify different subjects.

## 80/20 distribution

Default retained native solver families are A*, BFWS, and IW. The maintained Python domain catalog contains only explicit GraphDomain planning. Heavy RL/GPU, RDDL, flight-planning, scheduling/optimization, LP/POMDP, PDDL/PPDDL, tuning, notebook, and broad demonstration stacks are excluded from this fork.

Python multiprocessing is intentionally unsupported. Do not restore pathos, pynng, or dill to fan out planner work; ex4pm and the cloud scheduler own horizontal concurrency.

## Evidence

Use `UNKNOWN | PARTIAL_ALIVE | ALIVE | BLOCKED | BUILD_BROKEN | UNSUPPORTED` and typed `REFUSED`. A solver name in source is not ALIVE. ALIVE for a solve requires exact execution plus replay of the returned plan against the admitted problem. ALIVE from `verify_ggen_projection.py` applies only to the exact graph/projection-consistency subject it reports.

## Upstream

The fork baseline is `airbus/scikit-decide@138799ba44a9049ee9bb21a937c9ac669f043afd`. Preserve LICENSE/copyright notices and record future upstream rebases explicitly in `UPSTREAM.md`.

## Verification

Run the gates in this order:

```bash
python scripts/verify_ggen_projection.py
ggen sync run --dry-run
ggen sync run
ggen receipt verify
pytest -q tests/ex4pm_plan
python -m build --wheel
ex4pm-plan capabilities
```

Then execute an exact solve smoke and replay it. The CI workflow pins the ggen source identity used for manufacture. Do not expand CI back to upstream's full scientific/RL matrix unless the maintained capability set explicitly expands.
