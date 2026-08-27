import pytest

from ex4pm_plan.worker import PROTOCOL, capabilities, solve


def graph_request():
    return {
        "solver": "astar",
        "problem": {
            "type": "deterministic_graph",
            "initial": "A",
            "goals": ["G"],
            "edges": [
                {"from": "A", "to": "G", "action": "expensive", "cost": 5},
                {"from": "A", "to": "B", "action": "to_b", "cost": 1},
                {"from": "B", "to": "G", "action": "to_g", "cost": 1},
            ],
        },
    }


def test_capabilities_are_lean_and_construct_only():
    response = capabilities()
    assert response["protocol"] == PROTOCOL
    assert response["standing"] == "ALIVE"
    assert response["worker_solvers"] == ["astar"]
    assert response["library_solvers"] == ["astar", "bfws", "iw"]
    assert response["authority"] == "CONSTRUCT_ONLY"
    assert response["actuation"] is False


def test_retained_solver_wrappers_import_from_the_lean_extension():
    from skdecide.hub.solver.astar import Astar
    from skdecide.hub.solver.bfws import BFWS
    from skdecide.hub.solver.iw import IW

    assert Astar.__name__ == "Astar"
    assert BFWS.__name__ == "BFWS"
    assert IW.__name__ == "IW"


def test_astar_solves_and_replay_verifies_shortest_path():
    response = solve(graph_request())
    assert response["standing"] == "ALIVE"
    assert response["status"] == "ok"
    assert response["result"]["solved"] is True
    assert [step["action"] for step in response["result"]["steps"]] == ["to_b", "to_g"]
    assert response["result"]["total_cost"] == 2.0
    assert response["evidence"]["replay_verified"] is True
    assert response["evidence"]["subject_hash"].startswith("sha256:")
    assert response["evidence"]["result_hash"].startswith("sha256:")


def test_same_request_has_stable_subject_identity():
    first = solve(graph_request())
    second = solve(graph_request())
    assert first["evidence"]["subject_hash"] == second["evidence"]["subject_hash"]


def test_negative_cost_is_refused_before_solver_execution():
    request = graph_request()
    request["problem"]["edges"][0]["cost"] = -1
    response = solve(request)
    assert response["standing"] == "REFUSED"
    assert response["refusal"]["type"] == "INVALID_COST"


def test_heavy_solver_is_typed_unsupported():
    request = graph_request()
    request["solver"] = "ray_rllib"
    response = solve(request)
    assert response["standing"] == "UNSUPPORTED"
    assert response["reason"]["type"] == "UNSUPPORTED_SOLVER"


def test_python_parallel_mode_is_explicitly_unsupported():
    from skdecide.builders.solver.parallelability import ParallelSolver

    solver = ParallelSolver(parallel=True)
    with pytest.raises(RuntimeError, match="UNSUPPORTED"):
        solver.get_domain()
