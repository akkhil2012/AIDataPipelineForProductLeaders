# Data Platform Architecture (Colored Diagram)

The diagram below shows how the Spring Boot microservices, Python orchestration utilities, and UI artifacts in this repository
work together to turn raw product data into consumable insights.

```mermaid
flowchart LR
    classDef orchestrator fill:#FFF3E0,stroke:#F57C00,stroke-width:2,color:#E65100
    classDef service fill:#E3F2FD,stroke:#1A73E8,stroke-width:2,color:#0D47A1
    classDef data fill:#E8F5E9,stroke:#2E7D32,stroke-width:2,color:#1B5E20
    classDef platform fill:#F3E5F5,stroke:#8E24AA,stroke-width:2,color:#4A148C
    classDef ui fill:#E0F7FA,stroke:#00838F,stroke-width:2,color:#006064
    classDef integration fill:#FFFDE7,stroke:#FBC02D,stroke-width:2,color:#F57F17

    Raw(("Raw product events\n(sample_data.json)")):::data
    Config[["Pipeline config\n(pipeline_config.yaml)" ]]:::platform
    Orchestrator["Python orchestrator\nrun_pipeline.py"]:::orchestrator

    subgraph Microservices["Spring Boot microservices\n(docker-compose.yml)"]
        direction LR
        Ingest["Data Ingestion\nPort 8081"]:::service
        Dedup["Data Deduplication\nPort 8082"]:::service
        Quality["Data Quality\nPort 8083"]:::service
        Normalize["Data Normalization\nPort 8084"]:::service
        Storage["Data Storage\nPort 8085"]:::service
        Consume["Data Consumption\nPort 8086"]:::service
    end

    FastAPI[["Per-service Python\n/validate & /process"]]:::integration
    DB[("H2 / external DBs\nwith lineage")]:::data
    Metrics[["Actuator health + metrics\ncentral logging & retries"]]:::platform
    UI["Streamlit & dashboards\n(ui/) and insights"]:::ui

    Raw --> Orchestrator
    Config --> Orchestrator
    Orchestrator -->|POST payloads| Ingest --> Dedup --> Quality --> Normalize --> Storage --> Consume --> UI
    Storage --> DB
    Microservices -.-> Metrics
    Microservices --> FastAPI
```

**Color legend**
- **Orange:** Orchestration logic driven by `run_pipeline.py` and YAML configuration.
- **Blue:** Spring Boot microservices that implement each pipeline stage with consistent REST + Python integration endpoints.
- **Green:** Data assets and persistence layers (sample payloads, H2/external databases, lineage metadata).
- **Purple:** Platform scaffolding such as Docker Compose plus observability via Actuator, logging, and retries.
- **Teal:** Consumer experiences like the Streamlit UI and analytics dashboards.
- **Yellow:** Python FastAPI adapters that each service can call for validation or processing.

Use this diagram alongside [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md) and [`pipeline/README.md`](pipeline/README.md) when onboarding
new collaborators or explaining how the demo pipeline flows from raw events to analytics-ready outputs.
