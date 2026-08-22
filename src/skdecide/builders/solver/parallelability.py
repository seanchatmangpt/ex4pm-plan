# Copyright (c) AIRBUS and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

__all__ = ["ParallelSolver"]


class ParallelSolver:
    """Compatibility surface for retained scikit-decide solver wrappers.

    ex4pm-plan intentionally does not run Python multiprocessing workers.
    Horizontal fan-out belongs to ex4pm and the cloud scheduler, so the lean
    worker admits only ``parallel=False``. Keeping this class preserves the
    upstream solver constructor shape without restoring pathos/pynng/dill.
    """

    def __init__(self, parallel: bool = False, shared_memory_proxy=None):
        self._parallel = parallel
        self._shared_memory_proxy = shared_memory_proxy
        self._domain = None
        self._lambdas = []
        self._ipc_notify = False

    def _initialize(self):
        if self._parallel:
            raise RuntimeError(
                "parallel=True is UNSUPPORTED in ex4pm-plan; "
                "fan out independent planner workers through ex4pm/cloud scheduling"
            )
        self._domain = self._domain_factory()

    def close(self):
        self._domain = None

    def _cleanup(self):
        self.close()

    def get_domain(self):
        if self._domain is None:
            self._initialize()
        return self._domain

    def call_domain_method(self, name, *args):
        if self._parallel:
            raise RuntimeError(
                "parallel=True is UNSUPPORTED in ex4pm-plan; "
                "fan out independent planner workers through ex4pm/cloud scheduling"
            )
        return getattr(self.get_domain(), name)(*args)
