FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir build && python -m build

FROM python:3.12-slim
WORKDIR /app
RUN useradd -m -u 1000 appuser
COPY --from=builder /app/dist/*.whl .
RUN pip install --no-cache-dir *.whl && rm *.whl
USER appuser
ENTRYPOINT ["garmin-server"]
