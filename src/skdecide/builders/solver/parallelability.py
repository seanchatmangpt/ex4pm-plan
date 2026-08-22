# Copyright (c) AIRBUS and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

__all__ = ["ParallelSolver"]


class ParallelSolver:
    """Optional local multi-process execution for solvers that support it.

    The heavy multiprocessing/NNG Python dependencies are imported only when
    ``parallel=True``. ex4pm-plan's default cloud worker runs one solver per
    process and lets ex4pm own fan-out across workers.
    """

    def __init__(self, parallel: bool = False, shared_memory_proxy=None):
        self._parallel = parallel
        self._shared_memory_proxy = shared_memory_proxy
        self._domain = None
        self._lambdas = []
        self._ipc_notify = False

    def _initialize(self):
        if self._parallel:
            try:
                from skdecide.parallel_domains import PipeParallelDomain, ShmParallelDomain
            except ImportError as exc:
                raise RuntimeError(
                    "parallel solver mode requires ex4pm-plan[parallel]"
                ) from exc

            if self._shared_memory_proxy is None:
                self._domain = PipeParallelDomain(
                    self._domain_factory,
                    lambdas=self._lambdas,
                    ipc_notify=self._ipc_notify,
                )
            else:
                self._domain = ShmParallelDomain(
                    self._domain_factory,
                    self._shared_memory_proxy,
                    lambdas=self._lambdas,
                    ipc_notify=self._ipc_notify,
                )
            self._domain._launch_processes()
        else:
            self._domain = self._domain_factory()

    def close(self):
        if self._domain is not None and self._parallel:
            self._domain.close()
            self._domain = None

    def _cleanup(self):
        self.close()

    def get_domain(self):
        if self._domain is None:
            self._initialize()
        return self._domain

    def call_domain_method(self, name, *args):
        if self._parallel:
            process_id = getattr(self._domain, name)(*args)
            return self._domain.get_result(process_id)
        return getattr(self._domain, name)(*args)
