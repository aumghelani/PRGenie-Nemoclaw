"""
Generate comparison charts from Speed Demon benchmark results.

Reads JSON results from the results/ directory and produces:
  1. Baseline vs. Speculative throughput/latency bar chart
  2. Sweep chart: throughput and latency vs. num-speculative-tokens
  3. Per-workload breakdown

Usage:
    python3 plot_results.py
    python3 plot_results.py --results-dir ./results --output-dir ./charts
"""

import argparse
import json
import os

import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for headless servers


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def plot_baseline_vs_speculative(results_dir: str, output_dir: str):
    """Bar chart comparing baseline vs. speculative across workloads."""
    baseline_path = os.path.join(results_dir, "baseline.json")
    spec_path = os.path.join(results_dir, "speculative_k5.json")

    if not os.path.exists(baseline_path) or not os.path.exists(spec_path):
        print("  Skipping baseline vs. speculative chart (missing data)")
        return

    baseline = load_json(baseline_path)
    speculative = load_json(spec_path)

    workloads = list(baseline["workloads"].keys())
    x = range(len(workloads))
    width = 0.35

    # --- Throughput chart ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    baseline_tps = [baseline["workloads"][w]["aggregate_throughput_tps"] for w in workloads]
    spec_tps = [speculative["workloads"][w]["aggregate_throughput_tps"] for w in workloads]

    bars1 = ax1.bar([i - width / 2 for i in x], baseline_tps, width, label="Baseline (70B)", color="#4a90d9")
    bars2 = ax1.bar([i + width / 2 for i in x], spec_tps, width, label="Speculative (70B+8B)", color="#e74c3c")

    ax1.set_xlabel("Workload")
    ax1.set_ylabel("Throughput (tokens/sec)")
    ax1.set_title("Throughput: Baseline vs. Speculative Decoding")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(workloads, rotation=15)
    ax1.legend()
    ax1.bar_label(bars1, fmt="%.1f", fontsize=8)
    ax1.bar_label(bars2, fmt="%.1f", fontsize=8)

    # --- Latency chart ---
    baseline_lat = [baseline["workloads"][w]["latency_median_ms"] for w in workloads]
    spec_lat = [speculative["workloads"][w]["latency_median_ms"] for w in workloads]

    bars3 = ax2.bar([i - width / 2 for i in x], baseline_lat, width, label="Baseline (70B)", color="#4a90d9")
    bars4 = ax2.bar([i + width / 2 for i in x], spec_lat, width, label="Speculative (70B+8B)", color="#e74c3c")

    ax2.set_xlabel("Workload")
    ax2.set_ylabel("Median Latency (ms)")
    ax2.set_title("Latency: Baseline vs. Speculative Decoding")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(workloads, rotation=15)
    ax2.legend()
    ax2.bar_label(bars3, fmt="%.0f", fontsize=8)
    ax2.bar_label(bars4, fmt="%.0f", fontsize=8)

    plt.tight_layout()
    path = os.path.join(output_dir, "baseline_vs_speculative.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def plot_sweep(results_dir: str, output_dir: str):
    """Line chart showing throughput and latency vs. num-speculative-tokens."""
    summary_path = os.path.join(results_dir, "sweep_summary.json")
    if not os.path.exists(summary_path):
        print("  Skipping sweep chart (no sweep_summary.json)")
        return

    summary = load_json(summary_path)
    k_values = sorted(int(k) for k in summary.keys())

    workloads = list(next(iter(summary.values())).keys())
    colors = ["#4a90d9", "#e74c3c", "#2ecc71"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    for i, workload in enumerate(workloads):
        tps = [summary[str(k)][workload]["throughput_tps"] for k in k_values]
        lat = [summary[str(k)][workload]["latency_median_ms"] for k in k_values]

        ax1.plot(k_values, tps, "o-", label=workload, color=colors[i % len(colors)])
        ax2.plot(k_values, lat, "o-", label=workload, color=colors[i % len(colors)])

    ax1.set_xlabel("num-speculative-tokens (K)")
    ax1.set_ylabel("Throughput (tokens/sec)")
    ax1.set_title("Throughput vs. Speculation Depth")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.set_xlabel("num-speculative-tokens (K)")
    ax2.set_ylabel("Median Latency (ms)")
    ax2.set_title("Latency vs. Speculation Depth")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, "sweep_spec_tokens.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def plot_latency_distribution(results_dir: str, output_dir: str):
    """Box plot of per-request latency distribution for baseline vs. speculative."""
    baseline_path = os.path.join(results_dir, "baseline.json")
    spec_path = os.path.join(results_dir, "speculative_k5.json")

    if not os.path.exists(baseline_path) or not os.path.exists(spec_path):
        print("  Skipping latency distribution chart (missing data)")
        return

    baseline = load_json(baseline_path)
    speculative = load_json(spec_path)

    workloads = list(baseline["workloads"].keys())
    fig, axes = plt.subplots(1, len(workloads), figsize=(5 * len(workloads), 6))
    if len(workloads) == 1:
        axes = [axes]

    for i, workload in enumerate(workloads):
        b_latencies = [
            r["latency_s"] * 1000
            for r in baseline["workloads"][workload]["individual_results"]
        ]
        s_latencies = [
            r["latency_s"] * 1000
            for r in speculative["workloads"][workload]["individual_results"]
        ]

        bp = axes[i].boxplot(
            [b_latencies, s_latencies],
            labels=["Baseline", "Speculative"],
            patch_artist=True,
        )
        bp["boxes"][0].set_facecolor("#4a90d9")
        bp["boxes"][1].set_facecolor("#e74c3c")

        axes[i].set_title(workload)
        axes[i].set_ylabel("Latency (ms)")

    plt.suptitle("Latency Distribution: Baseline vs. Speculative Decoding", fontsize=14)
    plt.tight_layout()
    path = os.path.join(output_dir, "latency_distribution.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Plot Speed Demon results")
    parser.add_argument("--results-dir", default=os.path.join(os.path.dirname(__file__), "results"))
    parser.add_argument("--output-dir", default=os.path.join(os.path.dirname(__file__), "charts"))
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("Generating charts...")
    plot_baseline_vs_speculative(args.results_dir, args.output_dir)
    plot_sweep(args.results_dir, args.output_dir)
    plot_latency_distribution(args.results_dir, args.output_dir)
    print("\nDone! Charts saved to:", args.output_dir)


if __name__ == "__main__":
    main()
