#!/usr/bin/env python3
"""Independent admission court for the ggen-owned ex4pm-plan contract projection."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

try:
    from rdflib import Graph, Namespace, URIRef
    from rdflib.namespace import DCTERMS, PROV, SKOS
except ImportError as exc:  # pragma: no cover - environment classification
    print(
        json.dumps(
            {
                "standing": "BUILD_BROKEN",
                "error": {
                    "type": "MISSING_VERIFIER_DEPENDENCY",
                    "message": "rdflib is required to verify the admitted RDF graph",
                    "dependency": "rdflib",
                },
            },
            sort_keys=True,
        )
    )
    raise SystemExit(3) from exc


ROOT = Path(__file__).resolve().parents[1]
GGEN_CONFIG = ROOT / "ggen.toml"
PACK_ROOT = ROOT / "ggen" / "packs" / "ex4pm-plan-contract-pack"
PACK_MANIFEST = PACK_ROOT / "pack.toml"
ONTOLOGY = PACK_ROOT / "ontology.ttl"
TEMPLATE = PACK_ROOT / "templates" / "generated_contract.py.tmpl"
PROJECTION = ROOT / "src" / "ex4pm_plan" / "generated_contract.py"

EP = Namespace("https://w3id.org/ex4pm/plan#")
WORKER = EP.Worker
EXPECTED_UPSTREAM = URIRef(
    "https://github.com/airbus/scikit-decide/commit/"
    "138799ba44a9049ee9bb21a937c9ac669f043afd"
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _one(graph: Graph, subject: URIRef, predicate: URIRef) -> Any:
    values = list(graph.objects(subject, predicate))
    if len(values) != 1:
        raise ValueError(
            f"expected exactly one value for {subject.n3()} {predicate.n3()}, got {len(values)}"
        )
    return values[0]


def _notation(graph: Graph, node: URIRef) -> str:
    return str(_one(graph, node, SKOS.notation))


def _load_projection():
    spec = importlib.util.spec_from_file_location("ex4pm_plan_generated_contract", PROJECTION)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generated projection: {PROJECTION}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _refuse(code: str, message: str, **details: Any) -> int:
    payload: dict[str, Any] = {
        "standing": "REFUSED",
        "refusal": {"type": code, "message": message},
    }
    if details:
        payload["refusal"]["details"] = details
    print(json.dumps(payload, sort_keys=True))
    return 2


def main() -> int:
    required = [GGEN_CONFIG, PACK_MANIFEST, ONTOLOGY, TEMPLATE, PROJECTION]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        return _refuse(
            "MISSING_GGEN_SURFACE",
            "required ggen source or projection file is absent",
            missing=missing,
        )

    try:
        config = tomllib.loads(GGEN_CONFIG.read_text())
        manifest = tomllib.loads(PACK_MANIFEST.read_text())
        graph = Graph()
        graph.parse(ONTOLOGY, format="turtle")
        projection = _load_projection()

        if config.get("project", {}).get("name") != "ex4pm-plan":
            raise ValueError("ggen.toml project identity drift")
        pack = manifest.get("pack", {})
        if pack.get("name") != "ex4pm-plan-contract-pack":
            raise ValueError("pack identity drift")
        if not pack.get("version"):
            raise ValueError("pack version is missing")

        pack_config = config.get("packs", {}).get("ex4pm-plan-contract-pack", {})
        if pack_config.get("path") != "ggen/packs/ex4pm-plan-contract-pack":
            raise ValueError("consumer pack path drift")

        protocol = str(_one(graph, WORKER, DCTERMS.identifier))
        authority = str(_one(graph, WORKER, EP.authority))
        actuation_literal = str(_one(graph, WORKER, EP.actuation)).lower()
        if actuation_literal not in {"true", "false"}:
            raise ValueError("actuation must be the plain literal true or false")
        actuation = actuation_literal == "true"

        problem_node = _one(graph, WORKER, EP.problemType)
        worker_solver_node = _one(graph, WORKER, EP.workerSolver)
        library_solvers = sorted(
            _notation(graph, node) for node in graph.objects(WORKER, EP.librarySolver)
        )
        operations = sorted(
            _notation(graph, node) for node in graph.objects(WORKER, EP.operation)
        )
        upstream = _one(graph, WORKER, PROV.wasDerivedFrom)

        expected = {
            "PROTOCOL": protocol,
            "SUPPORTED_PROBLEM": _notation(graph, problem_node),
            "SUPPORTED_SOLVER": _notation(graph, worker_solver_node),
            "LIBRARY_SOLVERS": tuple(library_solvers),
            "OPERATIONS": tuple(operations),
            "AUTHORITY": authority,
            "ACTUATION": actuation,
        }
        observed = {name: getattr(projection, name) for name in expected}
        if observed != expected:
            return _refuse(
                "GENERATED_PROJECTION_DRIFT",
                "generated runtime constants do not match admitted RDF facts",
                expected={
                    k: list(v) if isinstance(v, tuple) else v for k, v in expected.items()
                },
                observed={
                    k: list(v) if isinstance(v, tuple) else v for k, v in observed.items()
                },
            )

        if upstream != EXPECTED_UPSTREAM:
            raise ValueError(f"upstream provenance drift: {upstream}")
        if authority != "CONSTRUCT_ONLY" or actuation:
            raise ValueError("authority fence violated")

        template_text = TEMPLATE.read_text()
        if 'to: "src/ex4pm_plan/generated_contract.py"' not in template_text:
            raise ValueError("template output destination drift")
        for query_name in ("contract:", "library_solvers:", "operations:"):
            if query_name not in template_text:
                raise ValueError(f"template missing SPARQL binding {query_name}")

        evidence = {
            "ggen_config": _sha256(GGEN_CONFIG),
            "pack_manifest": _sha256(PACK_MANIFEST),
            "ontology": _sha256(ONTOLOGY),
            "template": _sha256(TEMPLATE),
            "projection": _sha256(PROJECTION),
        }
        print(
            json.dumps(
                {
                    "standing": "ALIVE",
                    "subject": {
                        "kind": "ggen_projection_consistency",
                        "project": "ex4pm-plan",
                        "pack": "ex4pm-plan-contract-pack",
                    },
                    "authority": authority,
                    "actuation": actuation,
                    "checks": [
                        "ggen_project_wiring",
                        "pack_manifest",
                        "rdf_parse",
                        "public_ontology_provenance",
                        "runtime_projection_matches_rdf",
                        "authority_fence",
                        "template_bindings",
                    ],
                    "evidence": evidence,
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:
        return _refuse(
            "GGEN_CONTRACT_INVALID",
            "ggen contract admission failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )


if __name__ == "__main__":
    raise SystemExit(main())
