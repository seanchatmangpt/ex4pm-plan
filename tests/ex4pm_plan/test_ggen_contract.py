import ex4pm_plan.worker as worker
from ex4pm_plan import generated_contract


def test_runtime_capabilities_are_bound_to_generated_contract():
    response = worker.capabilities()

    assert response["standing"] == "ALIVE"
    assert response["protocol"] == generated_contract.PROTOCOL
    assert response["problem_types"] == [generated_contract.SUPPORTED_PROBLEM]
    assert response["worker_solvers"] == [generated_contract.SUPPORTED_SOLVER]
    assert response["library_solvers"] == list(generated_contract.LIBRARY_SOLVERS)
    assert response["operations"] == list(generated_contract.OPERATIONS)
    assert response["authority"] == generated_contract.AUTHORITY
    assert response["actuation"] is generated_contract.ACTUATION
    assert response["contract_hash"] == worker._contract_hash()
    assert response["contract_hash"].startswith("sha256:")


def test_authority_fence_refuses_actuation_before_planner(monkeypatch):
    monkeypatch.setattr(worker, "ACTUATION", True)

    response = worker.solve({})

    assert response["standing"] == "REFUSED"
    assert response["refusal"]["type"] == "AUTHORITY_FENCE_VIOLATION"
    assert response["refusal"]["details"]["actuation"] is True


def test_authority_fence_refuses_non_construct_authority(monkeypatch):
    monkeypatch.setattr(worker, "AUTHORITY", "DO")

    response = worker.capabilities()

    assert response["standing"] == "REFUSED"
    assert response["refusal"]["type"] == "AUTHORITY_FENCE_VIOLATION"
    assert response["refusal"]["details"]["authority"] == "DO"


def test_contract_hash_changes_when_contract_changes(monkeypatch):
    baseline = worker._contract_hash()
    monkeypatch.setattr(worker, "OPERATIONS", ("capabilities", "solve", "future"))
    changed = worker._contract_hash()

    assert changed != baseline
