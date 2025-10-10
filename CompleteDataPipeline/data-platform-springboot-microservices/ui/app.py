"""Streamlit UI to visualize data platform microservices pipeline."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
from pyvis.network import Network


@dataclass(frozen=True)
class ServiceNode:
    """Representation of a microservice within the data pipeline."""

    identifier: str
    label: str
    description: str
    compose_service: str


PIPELINE_STEPS: List[ServiceNode] = [
    ServiceNode(
        identifier="dataingestion-service",
        label="Data Ingestion",
        description=(
            "Collects data from product analytics sources and APIs, preparing it for "
            "downstream processing."
        ),
        compose_service="dataingestion-service",
    ),
    ServiceNode(
        identifier="datadeduplication-service",
        label="Data Deduplication",
        description=(
            "Removes duplicate records to ensure unique, high-quality data assets."
        ),
        compose_service="datadeduplication-service",
    ),
    ServiceNode(
        identifier="dataquality-service",
        label="Data Quality",
        description=(
            "Validates schema, completeness, and accuracy rules before persistence."
        ),
        compose_service="dataquality-service",
    ),
    ServiceNode(
        identifier="datalineage-service",
        label="Data Lineage",
        description=(
            "Captures lineage metadata so teams can trace transformations across the pipeline."
        ),
        compose_service="datalineage-service",
    ),
]

PIPELINE_EDGES = [
    (PIPELINE_STEPS[index].identifier, PIPELINE_STEPS[index + 1].identifier)
    for index in range(len(PIPELINE_STEPS) - 1)
]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
SERVICE_STATUS_KEY = "service_status"


def initialize_session_state() -> None:
    """Ensure the Streamlit session state contains a service status store."""

    if SERVICE_STATUS_KEY not in st.session_state:
        st.session_state[SERVICE_STATUS_KEY] = {}


def start_service_via_compose(service_name: str) -> Tuple[bool, str, str]:
    """Start a service using Docker Compose commands.

    Parameters
    ----------
    service_name:
        The name of the service as defined in the docker-compose file.

    Returns
    -------
    Tuple[bool, str, str]
        A tuple containing whether the command succeeded, a user-friendly message,
        and raw command output or diagnostic details.
    """

    if not COMPOSE_FILE.exists():
        return (
            False,
            f"Unable to locate docker-compose.yml at {COMPOSE_FILE}.",
            "Ensure the project is checked out with its Docker configuration.",
        )

    commands_to_try = (
        ["docker", "compose", "up", "-d", service_name],
        ["docker-compose", "up", "-d", service_name],
    )
    errors: List[str] = []

    for command in commands_to_try:
        try:
            result = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            errors.append(
                f"Command not found: {' '.join(command[:1 if command[0] != 'docker' else 2])}"
            )
            continue
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else str(exc)
            errors.append(stderr)
            continue

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        details = ["Command executed:", " ".join(command)]
        if stdout:
            details.append("Standard output:\n" + stdout)
        if stderr:
            details.append("Standard error:\n" + stderr)

        return True, f"Service '{service_name}' started successfully.", "\n\n".join(details)

    combined_details = "\n\n".join(errors) if errors else "Unknown error"
    return (
        False,
        f"Failed to start service '{service_name}'. See details below.",
        combined_details,
    )


def render_service_controls() -> None:
    """Render sidebar controls that allow users to start pipeline services."""

    st.sidebar.header("Service Controls")
    st.sidebar.caption(
        "Start individual microservices directly from this interface. Commands are "
        "executed using Docker Compose in detached mode."
    )

    if not COMPOSE_FILE.exists():
        st.sidebar.error(
            "docker-compose.yml was not found. Service actions are unavailable in this "
            "environment."
        )
        return

    status_store: Dict[str, Dict[str, str]] = st.session_state[SERVICE_STATUS_KEY]

    for node in PIPELINE_STEPS:
        section = st.sidebar.container()
        if section.button(f"Start {node.label}", key=f"start-{node.identifier}"):
            with st.spinner(f"Starting {node.label}..."):
                success, message, details = start_service_via_compose(node.compose_service)

            status_store[node.identifier] = {
                "success": success,
                "message": message,
                "details": details,
            }

        node_status = status_store.get(node.identifier)
        if node_status:
            if node_status["success"]:
                section.success(node_status["message"])
            else:
                section.error(node_status["message"])

            if node_status["details"]:
                with section.expander("Command details", expanded=False):
                    section.code(node_status["details"], language="bash")


def render_service_activity() -> None:
    """Display a summary of service start attempts in the main layout."""

    st.subheader("Service Activity Log")
    status_store: Dict[str, Dict[str, str]] = st.session_state[SERVICE_STATUS_KEY]

    if not status_store:
        st.info("No services have been started from this session yet.")
        return

    for node in PIPELINE_STEPS:
        node_status = status_store.get(node.identifier)
        if not node_status:
            continue

        message = f"{node.label}: {node_status['message']}"
        if node_status["success"]:
            st.success(message)
        else:
            st.error(message)

        if node_status["details"]:
            with st.expander(f"{node.label} – command output"):
                st.code(node_status["details"], language="bash")


def build_network() -> Network:
    """Create a PyVis network with the pipeline topology."""

    network = Network(
        height="600px",
        width="100%",
        bgcolor="#0f172a",
        font_color="white",
        directed=True,
    )
    network.barnes_hut()

    for node in PIPELINE_STEPS:
        network.add_node(
            node.identifier,
            label=node.label,
            title=f"{node.label}: {node.description}",
            color="#38bdf8",
        )

    for source, target in PIPELINE_EDGES:
        network.add_edge(source, target, color="#facc15", arrowStrikethrough=False)

    network.set_options(
        """
        var options = {
          "nodes": {
            "font": {"size": 18},
            "shape": "dot",
            "scaling": {"min": 15, "max": 40}
          },
          "edges": {
            "color": {"color": "#facc15"},
            "smooth": false,
            "arrows": {
              "to": {"enabled": true, "scaleFactor": 1.2}
            }
          },
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -8000,
              "springLength": 200,
              "springConstant": 0.04,
              "damping": 0.09
            },
            "minVelocity": 0.75
          }
        }
        """
    )

    return network


def main() -> None:
    st.set_page_config(page_title="Data Platform Pipeline", layout="wide")
    st.title("Data Platform Microservices Pipeline")
    st.markdown(
        """
        This topology view illustrates how the data platform microservices interact within
        the product insights pipeline. Each node represents a microservice, and edges indicate
        the order in which data flows through the pipeline.
        """
    )

    initialize_session_state()
    render_service_controls()

    network = build_network()
    graph_html = network.generate_html(notebook=False)

    st.components.v1.html(graph_html, height=620, scrolling=True)

    st.subheader("Pipeline Stage Details")
    for step_number, node in enumerate(PIPELINE_STEPS, start=1):
        with st.expander(f"{step_number}. {node.label}"):
            st.write(node.description)

    render_service_activity()


if __name__ == "__main__":
    main()
