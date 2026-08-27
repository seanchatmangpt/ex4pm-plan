# Copyright (c) AIRBUS and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""Stable cloud-worker projection for the lean ex4pm planning fork."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from ex4pm_plan.generated_contract import (
    ACTUATION,
    AUTHORITY,
    LIBRARY_SOLVERS,
    OPERATIONS,
    PROTOCOL,
    SUPPORTED_PROBLEM,
    SUPPORTED_SOLVER,
)
from skdecide.hub.domain.graph_domain.GraphDomain import GraphDomain
from skdecide.hub.solver.astar import Astar


def _package_version() -> str:
    try:
        return version("ex4pm-plan")
    except PackageNotFoundError:
        return "0+source"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _refused(code: str, message: str, **details: Any) -> dict[str, Any]:
    refusal = {"type": code, "message": message}
    if details:
        refusal["details"] = details
    return {
        "protocol": PROTOCOL,
        "status": "refused",
        "standing": "REFUSED",
        "refusal": refusal,
    }


def _unsupported(code: str, message: str, **details: Any) -> dict[str, Any]:
    reason = {"type": code, "message": message}
    if details:
        reason["details"] = details
    return {
        "protocol": PROTOCOL,
        "status": "unsupported",
        "standing": "UNSUPPORTED",
        "reason": reason,
    }


def _contract_subject() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "problem_types": [SUPPORTED_PROBLEM],
        "worker_solvers": [SUPPORTED_SOLVER],
        "library_solvers": list(LIBRARY_SOLVERS),
        "operations": list(OPERATIONS),
        "authority": AUTHORITY,
        "actuation": ACTUATION,
    }


def _contract_hash() -> str:
    return _hash(_contract_subject())


def _authority_fence() -> dict[str, Any] | None:
    if AUTHORITY == "CONSTRUCT_ONLY" and ACTUATION is False:
        return None
    return _refused(
        "AUTHORITY_FENCE_VIOLATION",
        "ggen contract must remain CONSTRUCT_ONLY with actuation disabled",
        authority=AUTHORITY,
        actuation=ACTUATION,
        contract_hash=_contract_hash(),
    )


def capabilities() -> dict[str, Any]:
    refusal = _authority_fence()
    if refusal is not None:
        return refusal

    return {
        "protocol": PROTOCOL,
        "status": "ok",
        "standing": "ALIVE",
        "subject": {"kind": "worker_operation", "operation": "capabilities"},
        "distribution": "ex4pm-plan",
        "version": _package_version(),
        "problem_types": [SUPPORTED_PROBLEM],
        "worker_solvers": [SUPPORTED_SOLVER],
        "library_solvers": list(LIBRARY_SOLVERS),
        "operations": list(OPERATIONS),
        "authority": AUTHORITY,
        "actuation": ACTUATION,
        "contract_hash": _contract_hash(),
    }


def _admit_problem(problem: Any) -> tuple[dict[str, Any], dict[str, Any]] | dict[str, Any]:
    if not isinstance(problem, dict):
        return _refused("INVALID_PROBLEM", "problem must be a JSON object")

    if problem.get("type") != SUPPORTED_PROBLEM:
        return _unsupported(
            "UNSUPPORTED_PROBLEM_TYPE",
            "the lean worker currently admits deterministic explicit graphs only",
            received=problem.get("type"),
            supported=[SUPPORTED_PROBLEM],
        )

    initial = problem.get("initial")
    goals = problem.get("goals")
    edges = problem.get("edges")

    if not isinstance(initial, str) or not initial:
        return _refused("INVALID_INITIAL_STATE", "initial must be a non-empty string")
    if not isinstance(goals, list) or not goals or not all(
        isinstance(goal, str) and goal for goal in goals
    ):
        return _refused("INVALID_GOALS", "goals must be a non-empty list of strings")
    if not isinstance(edges, list):
        return _refused("INVALID_EDGES", "edges must be a list")

    next_state_map: dict[str, dict[str, str]] = {}
    attributes: dict[str, dict[str, dict[str, float]]] = {}
    states = {initial, *goals}

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            return _refused("INVALID_EDGE", "each edge must be an object", index=index)

        source = edge.get("from")
        target = edge.get("to")
        action = edge.get("action")
        cost = edge.get("cost", 1.0)

        if not all(isinstance(value, str) and value for value in (source, target, action)):
            return _refused(
                "INVALID_EDGE_IDENTITY",
                "edge from/to/action must be non-empty strings",
                index=index,
            )
        if isinstance(cost, bool) or not isinstance(cost, (int, float)):
            return _refused("INVALID_COST", "edge cost must be numeric", index=index)
        cost = float(cost)
        if not math.isfinite(cost) or cost < 0:
            return _refused(
                "INVALID_COST",
                "A* worker admits finite non-negative edge costs",
                index=index,
                cost=cost,
            )

        source_actions = next_state_map.setdefault(source, {})
        source_attributes = attributes.setdefault(source, {})
        if action in source_actions:
            return _refused(
                "AMBIGUOUS_ACTION",
                "action labels must be unique within a source state",
                index=index,
                state=source,
                action=action,
            )

        source_actions[action] = target
        source_attributes[action] = {"weight": cost}
        states.update((source, target))

    for state in states:
        next_state_map.setdefault(state, {})
        attributes.setdefault(state, {})

    admitted = {
        "type": SUPPORTED_PROBLEM,
        "initial": initial,
        "goals": sorted(set(goals)),
        "edges": [
            {
                "from": source,
                "action": action,
                "to": target,
                "cost": attributes[source][action]["weight"],
            }
            for source in sorted(next_state_map)
            for action, target in sorted(next_state_map[source].items())
        ],
    }
    runtime = {
        "next_state_map": next_state_map,
        "attributes": attributes,
        "targets": set(goals),
    }
    return admitted, runtime


def solve(request: Any) -> dict[str, Any]:
    refusal = _authority_fence()
    if refusal is not None:
        return refusal

    if not isinstance(request, dict):
        return _refused("INVALID_REQUEST", "request must be a JSON object")

    solver_name = request.get("solver", SUPPORTED_SOLVER)
    if solver_name != SUPPORTED_SOLVER:
        return _unsupported(
            "UNSUPPORTED_SOLVER",
            "solver is not exposed by the lean cloud-worker contract",
            received=solver_name,
            supported=[SUPPORTED_SOLVER],
        )

    admitted_result = _admit_problem(request.get("problem"))
    if isinstance(admitted_result, dict):
        return admitted_result

    admitted, runtime = admitted_result
    contract_hash = _contract_hash()
    subject = {
        "protocol": PROTOCOL,
        "contract_hash": contract_hash,
        "solver": solver_name,
        "problem": admitted,
        "parameters": {"parallel": False},
    }

    try:
        domain = GraphDomain(
            runtime["next_state_map"],
            runtime["attributes"],
            targets=runtime["targets"],
        )
        with Astar(domain_factory=lambda: domain, parallel=False) as planner:
            planner.solve_from(admitted["initial"])
            raw_plan = planner.get_plan(admitted["initial"])
            explored_states = planner.get_nb_explored_states()
            solving_time_ms = planner.get_solving_time()
    except Exception as exc:
        return {
            "protocol": PROTOCOL,
            "status": "error",
            "standing": "BUILD_BROKEN",
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "evidence": {
                "contract_hash": contract_hash,
                "subject_hash": _hash(subject),
            },
        }

    current = admitted["initial"]
    total_cost = 0.0
    steps: list[dict[str, Any]] = []

    for state, action, _reported_value in raw_plan:
        if state != current:
            return {
                "protocol": PROTOCOL,
                "status": "error",
                "standing": "BUILD_BROKEN",
                "error": {
                    "type": "REPLAY_STATE_MISMATCH",
                    "message": "planner result did not replay against the admitted graph",
                },
                "evidence": {
                    "contract_hash": contract_hash,
                    "subject_hash": _hash(subject),
                },
            }
        if action not in runtime["next_state_map"].get(current, {}):
            return {
                "protocol": PROTOCOL,
                "status": "error",
                "standing": "BUILD_BROKEN",
                "error": {
                    "type": "REPLAY_ACTION_MISMATCH",
                    "message": "planner returned an action absent from the admitted graph",
                },
                "evidence": {
                    "contract_hash": contract_hash,
                    "subject_hash": _hash(subject),
                },
            }

        next_state = runtime["next_state_map"][current][action]
        cost = runtime["attributes"][current][action]["weight"]
        steps.append({"from": current, "action": action, "to": next_state, "cost": cost})
        total_cost += cost
        current = next_state

    solved = current in runtime["targets"]
    result = {
        "solved": solved,
        "initial": admitted["initial"],
        "goal": current if solved else None,
        "steps": steps,
        "total_cost": total_cost if solved else None,
    }

    return {
        "protocol": PROTOCOL,
        "status": "ok",
        "standing": "ALIVE",
        "subject": {
            "kind": "planner_invocation",
            "solver": solver_name,
            "problem_type": SUPPORTED_PROBLEM,
            "contract_hash": contract_hash,
        },
        "result": result,
        "metrics": {
            "explored_states": explored_states,
            "solving_time_ms": solving_time_ms,
        },
        "evidence": {
            "contract_hash": contract_hash,
            "subject_hash": _hash(subject),
            "result_hash": _hash(result),
            "replay_verified": True,
        },
    }


def handle(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        return _refused("INVALID_REQUEST", "request must be a JSON object")
    operation = request.get("op")
    if operation == "capabilities":
        return capabilities()
    if operation == "solve":
        return solve(request)
    return _unsupported(
        "UNSUPPORTED_OPERATION",
        "operation is not implemented by the lean worker",
        received=operation,
        supported=list(OPERATIONS),
    )


def _read_json(stream) -> Any:
    try:
        return json.load(stream)
    except json.JSONDecodeError as exc:
        return _refused(
            "INVALID_JSON",
            "stdin must contain one valid JSON object",
            line=exc.lineno,
            column=exc.colno,
        )


def _emit(value: Any) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ex4pm-plan")
    parser.add_argument(
        "command", choices=("capabilities", "solve", "worker"), help="worker operation"
    )
    args = parser.parse_args(argv)

    if args.command == "capabilities":
        response = capabilities()
        _emit(response)
        return 0 if response.get("standing") == "ALIVE" else 2

    if args.command == "solve":
        request = _read_json(sys.stdin)
        if isinstance(request, dict) and request.get("standing") == "REFUSED":
            _emit(request)
            return 2
        if not isinstance(request, dict):
            _emit(_refused("INVALID_REQUEST", "request must be a JSON object"))
            return 2
        response = solve(request)
        _emit(response)
        return 0 if response.get("standing") in {"ALIVE", "UNSUPPORTED"} else 2

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            _emit(
                _refused(
                    "INVALID_JSON",
                    "each worker input line must be valid JSON",
                    line=exc.lineno,
                    column=exc.colno,
                )
            )
            continue
        _emit(handle(request))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
