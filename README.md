# ex4pm-plan

`ex4pm-plan` is the 80/20 planning/search compute worker for [ex4pm](https://github.com/seanchatmangpt/ex4pm). It is a deliberately lean downstream distribution of [Airbus scikit-decide](https://github.com/airbus/scikit-decide), preserving its high-value domain/solver calculus and selected native search algorithms while physically removing unsupported heavyweight surfaces.

Upstream baseline: `airbus/scikit-decide@138799ba44a9049ee9bb21a937c9ac669f043afd`.

The upstream MIT license and AIRBUS copyright notices are preserved.

## Why this fork exists

ex4pm should use the BEAM for supervision, routing, admission, cloud placement, concurrency, budgets, authority, receipts, and replanning. Planner runtimes should be disposable compute capsules.

```text
ex4pm
  -> admit PlanningProblem
  -> select compatible planner compute
  -> authorize compute budget
  -> launch ex4pm-plan anywhere
  -> receive candidate plan
  -> independently validate
  -> BRCE / DO only in ex4pm
```

`ex4pm-plan` therefore has **CONSTRUCT authority only**. It computes candidate plans; it does not actuate external systems and does not claim to manufacture ex4pm receipts.

## The 80/20 cut

### Retained

- scikit-decide core domain/solver abstractions
- explicit deterministic `GraphDomain`
- native C++ A*
- native C++ BFWS
- native C++ IW
- A* exposed through the stable cloud-worker protocol
- deterministic admission, replay verification, and evidence hashes

### Removed

- Ray / RLlib
- Stable-Baselines3
- PyTorch / Torch Geometric
- JAX / Flax
- RDDL and Gurobi integrations
- flight-planning/cartography stacks
- discrete-optimization and scheduling stacks
- LP/POMDP solver families
- PDDL/PPDDL grounding stack, Clingo, and PEGTL
- Optuna tuning
- Python pathos/pynng/dill multiprocessing
- Binder, notebooks, docs, examples, stale JS tooling and upstream mega-lockfiles
- the upstream broad solver/domain test matrix

This is a physical trim: unretained solver/domain source subtrees are not shipped in the fork. If ex4pm later needs one of those capabilities, treat it as a new admitted edge rather than restoring an `all` extra.

## Stable worker protocol

Protocol identity: `ex4pm-plan/v1`.

Capabilities:

```bash
ex4pm-plan capabilities
```

A deterministic graph solve reads JSON from stdin:

```bash
cat <<'JSON' | ex4pm-plan solve
{
  "solver": "astar",
  "problem": {
    "type": "deterministic_graph",
    "initial": "A",
    "goals": ["G"],
    "edges": [
      {"from": "A", "to": "G", "action": "expensive", "cost": 5},
      {"from": "A", "to": "B", "action": "to_b", "cost": 1},
      {"from": "B", "to": "G", "action": "to_g", "cost": 1}
    ]
  }
}
JSON
```

The worker returns the replayed path, total cost, execution metrics, and deterministic SHA-256 evidence identities. `ALIVE` on a solve means the exact admitted planner invocation executed and its result replayed against the admitted graph. Invalid problems are typed `REFUSED`; non-retained capabilities are `UNSUPPORTED`.

For long-lived container workers, use newline-delimited JSON:

```bash
ex4pm-plan worker
```

Each line contains an `op`, currently `capabilities` or `solve`.

## Cloud container

```bash
git submodule update --init --recursive
docker build -t ex4pm-plan .
docker run --rm -i ex4pm-plan < requests.jsonl
```

The image is intended for ephemeral jobs on Kubernetes, AWS, Azure, GCP, Fly.io, or any OCI-capable scheduler. Cloud-provider credentials belong to ex4pm's execution broker, never inside this worker. Scale by launching more worker capsules; `parallel=True` inside Python is intentionally `UNSUPPORTED`.

## Development

```bash
git submodule update --init --recursive
python -m pip install -U pip
python -m pip install -e . pytest build
pytest -q tests/ex4pm_plan
python -m build --wheel
ex4pm-plan capabilities
```

The fork-specific CI validates only this maintained surface.

## Upstream correspondence

`skdecide` remains the Python namespace for retained upstream semantics. The distribution is named `ex4pm-plan`, and `src/ex4pm_plan/worker.py` is only a transport/projection layer over those semantics. Future upstream updates must be rebased or replayed from an exact Airbus commit with the slimming patch explicit; see `UPSTREAM.md`.
