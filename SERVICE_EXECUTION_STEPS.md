# Running the AI Data Pipeline Services Locally

This guide summarises how to bring up every component in the repository so you can exercise the end-to-end pipeline. It combines the microservice documentation, orchestration README, and Docker configuration that ship with the project.

## 1. Prepare your environment

1. Install Java 11+ and Maven 3.6+ so the Spring Boot services can compile and run locally.【F:CompleteDataPipeline/data-platform-springboot-microservices/dataingestion-service/README.md†L49-L66】【F:CompleteDataPipeline/data-platform-springboot-microservices/datadeduplication-service/README.md†L49-L66】
2. Ensure Python 3.9+ is available if you plan to run the pipeline orchestrator or Python FastAPI helpers.【F:CompleteDataPipeline/data-platform-springboot-microservices/pipeline/README.md†L94-L111】【F:CompleteDataPipeline/data-platform-springboot-microservices/dataingestion-service/README.md†L67-L102】
3. (Optional) Install Docker Desktop if you prefer to start everything with Docker Compose rather than Maven.【F:CompleteDataPipeline/data-platform-springboot-microservices/pipeline/README.md†L90-L99】

## 2. Start the Spring Boot microservices

### Option A – Docker Compose

1. Change into the microservices directory:
   ```bash
   cd CompleteDataPipeline/data-platform-springboot-microservices
   ```
2. Build and launch the containers:
   ```bash
   docker-compose up --build
   ```
   This spins up the data ingestion (8081), deduplication (8082), data quality (8083), data storage (8085), and supporting Python FastAPI (8000) services defined in `docker-compose.yml`. Add normalization and consumption services by mirroring the existing entries if you need the full set of six stages.【F:CompleteDataPipeline/data-platform-springboot-microservices/pipeline/README.md†L90-L107】【F:CompleteDataPipeline/data-platform-springboot-microservices/docker-compose.yml†L1-L48】

### Option B – Maven per service

Run each service from its folder if you prefer not to use containers:

```bash
cd CompleteDataPipeline/data-platform-springboot-microservices/<service-folder>
mvn spring-boot:run
```

| Service folder | Default port |
|----------------|--------------|
| `dataingestion-service` | 8081 |
| `datadeduplication-service` | 8082 |
| `dataquality-service` | 8083 |
| `datanormalization-service`* | 8084 |
| `datastorage-service`* | 8085 |
| `dataconsumption-service`* | 8086 |

\*Some forks of the repository include these additional modules. If they are missing from your clone, follow the existing service pattern to add them or rely on the Docker Compose stack, which can be extended with matching entries for the remaining ports.【F:CompleteDataPipeline/data-platform-springboot-microservices/pipeline/README.md†L6-L87】【F:CompleteDataPipeline/data-platform-springboot-microservices/docker-compose.yml†L1-L48】

Each service exposes CRUD APIs plus `/process` and `/validate` endpoints that can call a Python FastAPI helper if you set `python.fastapi.base.url` (defaults to `http://localhost:8000`). Health checks are available via `/actuator/health`.【F:CompleteDataPipeline/data-platform-springboot-microservices/dataingestion-service/README.md†L15-L111】【F:CompleteDataPipeline/data-platform-springboot-microservices/datadeduplication-service/README.md†L15-L111】【F:CompleteDataPipeline/data-platform-springboot-microservices/pipeline/README.md†L6-L87】

## 3. (Optional) Start the Python FastAPI helper

The Docker Compose stack provides a placeholder container on port 8000. When running services via Maven, launch your own FastAPI process so the `/process` and `/validate` endpoints succeed, or use the services without Python integration by disabling those calls.【F:CompleteDataPipeline/data-platform-springboot-microservices/docker-compose.yml†L31-L48】【F:CompleteDataPipeline/data-platform-springboot-microservices/dataingestion-service/README.md†L92-L111】

## 4. Install orchestration dependencies

If you want to drive the full pipeline from Python, install the CLI requirements once:

```bash
pip install requests pyyaml
```

This enables the orchestrator to call each service stage and handle retries/logging defined in `pipeline_config.yaml`.【F:CompleteDataPipeline/data-platform-springboot-microservices/pipeline/README.md†L100-L133】

## 5. Execute the pipeline

With all services running, trigger the end-to-end pipeline from the repository root:

```bash
python CompleteDataPipeline/data-platform-springboot-microservices/pipeline/run_pipeline.py --log-level INFO
```

The script will load `sample_data.json`, post records to each microservice in sequence, and print stage-by-stage summaries. Use `--simulate` to dry-run without making HTTP requests—helpful if some services are offline while you test connectivity or payload transformations.【F:CompleteDataPipeline/data-platform-springboot-microservices/pipeline/README.md†L34-L135】

## 6. Validate the services

- Open `http://localhost:<port>/actuator/health` for each service to confirm it reports `UP`.
- Access the H2 console at `http://localhost:<port>/h2-console` (JDBC URL `jdbc:h2:mem:<service>db`, user `sa`, password `password`) to inspect stored records while running in development mode.【F:CompleteDataPipeline/data-platform-springboot-microservices/dataingestion-service/README.md†L79-L111】【F:CompleteDataPipeline/data-platform-springboot-microservices/datadeduplication-service/README.md†L79-L111】
- Review the pipeline output to see which records were ingested, deduplicated, validated, and published for consumption.【F:CompleteDataPipeline/data-platform-springboot-microservices/pipeline/run_pipeline.py†L74-L300】

Following these steps reproduces the complete AI data pipeline showcased in the project README so product leaders and engineers can experiment with the architecture, orchestration tooling, and governance assets locally.【F:README.md†L33-L87】
