# sensor data collector

`sensor data collector` is a small, production-shaped FastAPI service for ingesting
three-dimensional sensor measurements:

```json
{"foo": 10, "bar": 20, "buzz": 30}
```

The service consumes messages through a Kafka abstraction, classifies each measurement,
logs anomalies, sanitizes accepted data, and persists it to PostgreSQL. Kafka is
intentionally mocked for this demonstration: provisioning a real broker would obscure
the application behavior this project is designed to showcase. The mock is isolated
behind an injectable consumer interface, so a real Kafka adapter can be introduced
without changing the business layer.

## Processing rules

Thresholds are configured in [`config/settings.yaml`](config/settings.yaml) and are
inclusive:

| Field  | Accepted range       |
|--------|----------------------|
| `foo`  | `-100` through `100` |
| `bar`  | `-100` through `100` |
| `buzz` | `-100` through `100` |

- A valid measurement inside all three ranges is rounded to four decimal places and
  stored in PostgreSQL.
- A valid measurement with one or more values outside the ranges is an outlier. It is
  not stored and is emitted at `WARNING` level as
  `outlier detected: {JSON_PAYLOAD}`.
- A structurally valid request containing a non-numeric sensor value is invalid. It is
  not stored, is emitted at `ERROR` level as
  `invalid sensor data: {JSON_PAYLOAD}`, and returns HTTP `400`.
- The API uses version `v1` for business endpoints. The operational health check is
  intentionally unversioned.

Thresholds can be overridden with environment variables such as `FOO_MAX`, `BAR_MIN`,
and `BUZZ_MAX`.

## Run the application with Docker Compose

Requirements: Docker Desktop with Docker Compose.

```bash
docker compose up --build
```

The services are available at:

- API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Check readiness:

```bash
curl http://localhost:8000/health
```

For a clean demo database, remove the persisted PostgreSQL volume before starting:

```bash
docker compose down --volumes --remove-orphans
docker compose up --build
```

The volume removal is destructive and deletes the local demo data.

## Demonstrate the API

The demo publish endpoint is the presentation-friendly entry point to the mocked Kafka
consumer. In a production deployment, this endpoint would be replaced or complemented
by the actual broker adapter.

### Successful measurement

This is persisted after sanitization and returns `202 Accepted`:

```bash
curl --request POST http://localhost:8000/api/v1/demo/messages \
  --header 'content-type: application/json' \
  --data '{"foo":10,"bar":20,"buzz":30}'
```

### Outlier measurement

`foo=1000` is outside the configured range. The request returns `202`, the record is
not persisted, and the app container emits a warning:

```bash
curl --request POST http://localhost:8000/api/v1/demo/messages \
  --header 'content-type: application/json' \
  --data '{"foo":1000,"bar":20,"buzz":30}'

docker compose logs app
```

Expected log message:

```text
WARNING: outlier detected: {"foo":1000,"bar":20,"buzz":30}
```

### Invalid measurement

`buzz` is not numeric. The request returns `400` and is logged at error level:

```bash
curl --request POST http://localhost:8000/api/v1/demo/messages \
  --header 'content-type: application/json' \
  --data '{"foo":10,"bar":20,"buzz":"invalid"}'
```

Expected response:

```json
{"detail":"invalid sensor payload"}
```

### List persisted measurements

The endpoint supports page-based pagination:

```bash
curl 'http://localhost:8000/api/v1/measurements?page=1&page_size=20'
```

Operational health remains unversioned:

```bash
curl http://localhost:8000/health
```

## Run locally

The application itself requires PostgreSQL. Docker Compose is the recommended local
runtime because it provides the database with the same configuration used by the demo.

For Python development and unit tests:

```bash
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
python3 -m pytest -q
```

The unit and API tests use in-memory fakes for persistence and do not require Docker or
PostgreSQL.

## Code quality

Ruff is used as both formatter and linter:

```bash
python3 -m ruff format --check .
python3 -m ruff check .
```

Apply automatic fixes locally:

```bash
python3 -m ruff format .
python3 -m ruff check . --fix
```

## CI/CD pipeline

Example pipeline: Please see [https://github.com/jmaster1985/suen-demo/actions/runs/35343995527](https://github.com/jmaster1985/suen-demo/actions/runs/35343995527)

The workflow in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) is intentionally
structured as a promotion pipeline: inexpensive deterministic checks run first, and
container-level verification runs only after code quality passes.

1. **Quality gate** checks out the repository, installs the locked project dependency
   ranges, verifies formatting, runs Ruff linting, and executes the unit test suite.
2. **Container build and E2E verification** builds the exact application image that is
   tested, starts the application and PostgreSQL with Docker Compose, waits for
   `/health`, then exercises successful, outlier, invalid, and paginated-read flows
   through the real HTTP boundary.
3. **Diagnostics and cleanup** always publishes application logs and removes containers,
   networks, and volumes, including on failure.
4. **Registry publication placeholder** is present but disabled. It is the controlled
   location to add registry authentication, image signing/tagging, and `docker push`.
5. **Deployment placeholder** is also disabled. It is the controlled location to add
   environment-specific credentials, approval gates, and deployment commands.

The workflow uses least-privilege repository permissions, cancels obsolete runs for the
same ref, and tags the build image with the commit SHA to make artifacts traceable.
