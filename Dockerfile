FROM python:3.12-slim AS build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git libboost-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY . .
RUN python -m pip install --no-cache-dir "cmake>=3.26,<4" ninja \
    && python -m pip wheel --no-cache-dir . -w /wheels

FROM python:3.12-slim
COPY --from=build /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels ex4pm-plan \
    && rm -rf /wheels

USER nobody
ENTRYPOINT ["ex4pm-plan", "worker"]
