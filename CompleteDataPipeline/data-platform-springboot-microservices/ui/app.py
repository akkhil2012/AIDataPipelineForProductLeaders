"""Streamlit UI to visualize data platform microservices pipeline."""
from __future__ import annotations

import subprocess
import time
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
LOG_MODAL_KEY = "active_log_modal"


def initialize_session_state() -> None:
    """Ensure the Streamlit session state contains a service status store."""

    if SERVICE_STATUS_KEY not in st.session_state:
        st.session_state[SERVICE_STATUS_KEY] = {}
    if LOG_MODAL_KEY not in st.session_state:
        st.session_state[LOG_MODAL_KEY] = None


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


def fetch_service_logs(service_name: str) -> Tuple[bool, str]:
    """Retrieve recent logs for a service using Docker Compose."""

    if not COMPOSE_FILE.exists():
        return False, "docker-compose.yml is missing. Unable to fetch logs."

    commands_to_try = (
        ["docker", "compose", "logs", "--tail", "200", service_name],
        ["docker-compose", "logs", "--tail", "200", service_name],
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
        if stdout and stderr:
            return True, f"{stdout}\n\n{stderr}"
        if stdout:
            return True, stdout
        if stderr:
            return True, stderr
        return True, "No log output was produced."

    combined_details = "\n\n".join(errors) if errors else "Unknown error"
    return False, combined_details


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
        progress_placeholder = section.empty()
        if section.button(f"Start {node.label}", key=f"start-{node.identifier}"):
            progress_bar = progress_placeholder.progress(
                5, text=f"Initializing {node.label} startup..."
            )
            success, message, details = start_service_via_compose(node.compose_service)
            progress_bar.progress(65, text=f"{node.label} container launch in progress...")

            logs_success, logs = (False, "")
            if success:
                logs_success, logs = fetch_service_logs(node.compose_service)
            else:
                logs = "Service failed to start. Review the command output for more details."

            progress_bar.progress(100, text=f"{node.label} startup routine finished.")
            time.sleep(0.4)
            progress_placeholder.empty()

            status_store[node.identifier] = {
                "success": success,
                "message": message,
                "details": details,
                "logs": logs if logs_success or logs else "No logs available.",
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


def render_log_panel() -> None:
    """Render a panel that allows users to view Spring Boot logs."""

    st.subheader("Spring Boot Logs")
    status_store: Dict[str, Dict[str, str]] = st.session_state[SERVICE_STATUS_KEY]

    services_with_logs = [
        node
        for node in PIPELINE_STEPS
        if node.identifier in status_store and status_store[node.identifier].get("logs")
    ]

    if not services_with_logs:
        st.info("Start a service to view its Spring Boot logs here.")
        return

    options = {node.label: node.identifier for node in services_with_logs}
    selected_label = st.selectbox("Select a service", list(options.keys()))
    selected_identifier = options[selected_label]

    if st.button("Open log viewer", key=f"open-modal-{selected_identifier}"):
        st.session_state[LOG_MODAL_KEY] = selected_identifier

    st.caption("Logs are captured using docker compose tail commands once the service starts.")

    if st.session_state[LOG_MODAL_KEY]:
        modal_service_id = st.session_state[LOG_MODAL_KEY]
        modal_node = next(
            (node for node in PIPELINE_STEPS if node.identifier == modal_service_id),
            None,
        )
        if modal_node:
            node_logs = status_store.get(modal_service_id, {}).get("logs", "No logs available.")
            with st.modal(f"{modal_node.label} – Spring Boot Logs"):
                st.code(node_logs, language="bash")
                if st.button("Close log viewer", key="close-log-modal"):
                    st.session_state[LOG_MODAL_KEY] = None
        else:
            st.session_state[LOG_MODAL_KEY] = None


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

    topology_column, log_column = st.columns((2, 1), gap="large")

    with topology_column:
        st.components.v1.html(graph_html, height=620, scrolling=True)

        st.subheader("Pipeline Stage Details")
        for step_number, node in enumerate(PIPELINE_STEPS, start=1):
            with st.expander(f"{step_number}. {node.label}"):
                st.write(node.description)

        render_service_activity()

    with log_column:
        render_log_panel()


if __name__ == "__main__":
    main()
