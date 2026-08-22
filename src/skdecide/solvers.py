# Copyright (c) AIRBUS and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Base solver classes for the lean ex4pm-plan distribution."""

from __future__ import annotations

from collections.abc import Callable

from skdecide import autocast_all
from skdecide.builders.solver.fromanystatesolvability import FromInitialState
from skdecide.builders.solver.policy import DeterministicPolicies
from skdecide.domains import Domain

__all__ = ["Solver", "DeterministicPolicySolver"]


class Hyperparametrizable:
    """Compatibility marker without the discrete-optimization dependency.

    The 80/20 fork does not expose Optuna/discrete-optimization tuning. Retained
    solvers can still declare a ``hyperparameters`` list without making that
    heavyweight package a mandatory dependency of every planner worker.
    """

    hyperparameters = []

    @classmethod
    def get_hyperparameters(cls):
        return list(getattr(cls, "hyperparameters", []))


class Solver(Hyperparametrizable, FromInitialState):
    """Highest-level base solver class used by retained scikit-decide solvers."""

    T_domain = Domain
    _already_autocast = False

    def __init__(self, domain_factory: Callable[[], Domain]):
        def cast_domain_factory():
            domain = domain_factory()
            autocast_all(domain, domain, self.T_domain)
            return domain

        self._domain_factory = cast_domain_factory
        self._original_domain_factory = domain_factory
        original_domain_cls = type(self._original_domain_factory())
        autocast_all(self, self.T_domain, original_domain_cls)

    @property
    def domain_factory(self) -> Callable[[], Domain]:
        return self._domain_factory

    @property
    def original_domain_factory(self) -> Callable[[], Domain]:
        return self._original_domain_factory

    @classmethod
    def get_domain_requirements(cls) -> list[type]:
        def is_domain_builder(builder_cls):
            remove_ancestors = []
            while True:
                bases = builder_cls.__bases__
                if len(bases) == 0:
                    return True, remove_ancestors
                if len(bases) == 1:
                    builder_cls = bases[0]
                    remove_ancestors.append(builder_cls)
                else:
                    return False, []

        index = 0
        sorted_ancestors = list(cls.T_domain.__mro__[:-1])
        while index < len(sorted_ancestors):
            ancestor = sorted_ancestors[index]
            is_builder, remove_ancestors = is_domain_builder(ancestor)
            if is_builder:
                sorted_ancestors = [
                    candidate
                    for candidate in sorted_ancestors
                    if candidate not in remove_ancestors
                ]
                index += 1
            else:
                sorted_ancestors.remove(ancestor)
        return sorted_ancestors

    @classmethod
    def check_domain(cls, domain: Domain) -> bool:
        return all(
            isinstance(domain, requirement)
            for requirement in cls.get_domain_requirements()
        ) and cls._check_domain_additional(domain)

    @classmethod
    def _check_domain_additional(cls, domain: Domain) -> bool:
        return True

    def reset(self) -> None:
        return self._reset()

    def _reset(self) -> None:
        pass

    def _initialize(self):
        pass

    def _cleanup(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        self._cleanup()


class DeterministicPolicySolver(Solver, FromInitialState, DeterministicPolicies):
    """Typical deterministic-policy solver combination."""

    pass
