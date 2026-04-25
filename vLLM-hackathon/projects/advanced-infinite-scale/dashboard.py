"""
Infinite Scale — Real-time Scaling Dashboard

Terminal-based dashboard showing:
  - Pod status per component (prefill, decode, gateway)
  - GPU utilization across all cards
  - Key vLLM/llm-d metrics (throughput, TTFT, queue depth, KV-cache)

Usage:
    # Make sure port-forwards are running:
    kubectl port-forward -n llm-d svc/llm-d-gateway 8000:8000 &
    kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 &

    python3 dashboard.py
"""

import json
import subprocess
import time

import httpx
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

console = Console()

GATEWAY_URL = "http://localhost:8000"
PROMETHEUS_URL = "http://localhost:9090"


def get_gpu_stats() -> list[dict]:
    """Query nvidia-smi for GPU stats."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=5,
        )
        gpus = []
        for line in result.stdout.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 6:
                gpus.append({
                    "id": parts[0],
                    "name": parts[1],
                    "util": f"{parts[2]}%",
                    "mem_used": int(parts[3]),
                    "mem_total": int(parts[4]),
                    "mem_pct": f"{int(parts[3]) / int(parts[4]) * 100:.0f}%",
                    "temp": f"{parts[5]}C",
                })
        return gpus
    except Exception:
        return []


def get_pod_status(namespace: str = "llm-d") -> list[dict]:
    """Get pod status from kubectl."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
            capture_output=True, text=True, timeout=10,
        )
        pods_data = json.loads(result.stdout).get("items", [])
        pods = []
        for pod in pods_data:
            name = pod["metadata"]["name"]
            phase = pod["status"].get("phase", "Unknown")
            restarts = sum(
                cs.get("restartCount", 0)
                for cs in pod["status"].get("containerStatuses", [])
            )
            ready_containers = sum(
                1 for cs in pod["status"].get("containerStatuses", [])
                if cs.get("ready", False)
            )
            total_containers = len(pod["spec"].get("containers", []))
            pods.append({
                "name": name[:40],
                "phase": phase,
                "ready": f"{ready_containers}/{total_containers}",
                "restarts": str(restarts),
            })
        return pods
    except Exception:
        return [{"name": "kubectl error", "phase": "N/A", "ready": "-", "restarts": "-"}]


def query_prometheus(query: str) -> str:
    """Run an instant PromQL query and return the value."""
    try:
        r = httpx.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5,
        )
        results = r.json().get("data", {}).get("result", [])
        if results:
            return results[0]["value"][1]
        return "N/A"
    except Exception:
        return "N/A"


def get_vllm_health() -> str:
    """Check gateway health."""
    try:
        r = httpx.get(f"{GATEWAY_URL}/health", timeout=3)
        return "Healthy" if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception:
        return "Unreachable"


def build_dashboard() -> Layout:
    """Build the full terminal dashboard layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )

    # Header
    gateway_health = get_vllm_health()
    health_color = "green" if gateway_health == "Healthy" else "red"
    layout["header"].update(
        Panel(
            f"[bold]Infinite Scale Dashboard[/bold]  |  "
            f"Gateway: [{health_color}]{gateway_health}[/{health_color}]  |  "
            f"{time.strftime('%H:%M:%S')}",
            style="bold white on blue",
        )
    )

    # Left: Pods + Metrics
    left_layout = Layout()
    left_layout.split_column(
        Layout(name="pods"),
        Layout(name="metrics", size=10),
    )

    # Pod table
    pod_table = Table(title="Pods (llm-d namespace)", expand=True)
    pod_table.add_column("Name", style="cyan", max_width=40)
    pod_table.add_column("Status", style="green")
    pod_table.add_column("Ready")
    pod_table.add_column("Restarts")

    for pod in get_pod_status():
        status_style = "green" if pod["phase"] == "Running" else "yellow"
        pod_table.add_row(
            pod["name"],
            f"[{status_style}]{pod['phase']}[/{status_style}]",
            pod["ready"],
            pod["restarts"],
        )
    left_layout["pods"].update(Panel(pod_table))

    # Inference metrics
    metrics_table = Table(title="Inference Metrics", expand=True)
    metrics_table.add_column("Metric", style="bold")
    metrics_table.add_column("Value", justify="right")

    metrics = [
        ("Throughput (tok/s)", "llm_d:throughput:tokens_per_second"),
        ("Avg TTFT (s)", "llm_d:ttft:avg_seconds"),
        ("KV-Cache Util", "llm_d:kv_cache:avg_utilization"),
        ("Queue Depth", "llm_d:queue:total_waiting"),
        ("Active Requests", "llm_d:requests:active"),
    ]
    for name, query in metrics:
        value = query_prometheus(query)
        try:
            value = f"{float(value):.2f}"
        except (ValueError, TypeError):
            pass
        metrics_table.add_row(name, value)

    left_layout["metrics"].update(Panel(metrics_table))
    layout["left"].update(left_layout)

    # Right: GPU stats
    gpu_table = Table(title="GPU Utilization", expand=True)
    gpu_table.add_column("GPU", style="cyan")
    gpu_table.add_column("Name")
    gpu_table.add_column("Util", justify="right")
    gpu_table.add_column("VRAM", justify="right")
    gpu_table.add_column("Temp", justify="right")

    for gpu in get_gpu_stats():
        gpu_table.add_row(
            f"GPU {gpu['id']}", gpu["name"],
            gpu["util"], f"{gpu['mem_used']}/{gpu['mem_total']}MB ({gpu['mem_pct']})",
            gpu["temp"],
        )

    layout["right"].update(Panel(gpu_table))

    # Footer
    layout["footer"].update(
        Panel("[dim]Press Ctrl+C to exit  |  Refresh: 2s[/dim]", style="dim")
    )

    return layout


def main():
    print("Starting dashboard... (Ctrl+C to exit)")
    print("Tip: Run port-forwards first:")
    print("  kubectl port-forward -n llm-d svc/llm-d-gateway 8000:8000 &")
    print("  kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 &")
    print()

    try:
        with Live(build_dashboard(), console=console, refresh_per_second=0.5) as live:
            while True:
                live.update(build_dashboard())
                time.sleep(2)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
