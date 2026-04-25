"""
Compress & Compare — Generate quality vs. speed trade-off charts.

Reads benchmark and evaluation results from results/ and produces:
  1. Throughput vs. VRAM scatter plot (the Pareto frontier)
  2. Quality vs. speed bar chart
  3. Summary comparison table

Usage:
    python3 plot_tradeoffs.py
"""

import glob
import json
import os

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
CHARTS_DIR = os.path.join(SCRIPT_DIR, "charts")


def load_benchmarks() -> list[dict]:
    """Load throughput benchmark results."""
    results = []
    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, "bench_*.json"))):
        with open(path) as f:
            results.append(json.load(f))
    return results


def load_quality_scores() -> dict:
    """Load lm-eval quality results. Returns {variant: {task: score}}."""
    scores = {}
    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, "quality_*.json"))):
        with open(path) as f:
            data = json.load(f)
        # Extract variant name from filename
        basename = os.path.basename(path).replace("quality_", "").replace(".json", "")
        # lm-eval output structure varies; try common formats
        if "results" in data:
            task_scores = {}
            for task, metrics in data["results"].items():
                # Look for accuracy-like metrics
                for key in ["acc", "acc_norm", "accuracy"]:
                    if key in metrics:
                        task_scores[task] = metrics[key]
                        break
            scores[basename] = task_scores
    return scores


def plot_throughput_vs_vram(benchmarks: list[dict]):
    """Scatter plot: throughput vs VRAM usage."""
    if not benchmarks:
        print("  Skipping throughput vs VRAM chart (no benchmark data)")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = {"original": "#4a90d9", "gptq_4bit": "#e74c3c", "awq_4bit": "#2ecc71"}

    for b in benchmarks:
        variant = b["variant"]
        color = colors.get(variant, "#999999")
        ax.scatter(
            b["gpu_memory_mb"] / 1024,  # Convert to GB
            b["throughput_tps"],
            s=200, c=color, label=variant, zorder=5, edgecolors="white", linewidth=2,
        )
        ax.annotate(
            f"  {variant}\n  {b['throughput_tps']:.1f} tok/s",
            (b["gpu_memory_mb"] / 1024, b["throughput_tps"]),
            fontsize=9,
        )

    ax.set_xlabel("VRAM Usage (GB)", fontsize=12)
    ax.set_ylabel("Throughput (tokens/sec)", fontsize=12)
    ax.set_title("Quantization Trade-off: Throughput vs. VRAM", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "throughput_vs_vram.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def plot_comparison_bars(benchmarks: list[dict]):
    """Bar chart comparing throughput and latency across variants."""
    if not benchmarks:
        print("  Skipping comparison bar chart (no benchmark data)")
        return

    variants = [b["variant"] for b in benchmarks]
    throughputs = [b["throughput_tps"] for b in benchmarks]
    latencies = [b["latency_median_ms"] for b in benchmarks]
    vram = [b["gpu_memory_mb"] / 1024 for b in benchmarks]
    colors = ["#4a90d9", "#e74c3c", "#2ecc71"][:len(variants)]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Throughput
    bars = axes[0].bar(variants, throughputs, color=colors)
    axes[0].set_title("Throughput (tokens/sec)")
    axes[0].set_ylabel("tok/s")
    axes[0].bar_label(bars, fmt="%.1f")

    # Latency
    bars = axes[1].bar(variants, latencies, color=colors)
    axes[1].set_title("Median Latency (ms)")
    axes[1].set_ylabel("ms")
    axes[1].bar_label(bars, fmt="%.0f")

    # VRAM
    bars = axes[2].bar(variants, vram, color=colors)
    axes[2].set_title("VRAM Usage (GB)")
    axes[2].set_ylabel("GB")
    axes[2].bar_label(bars, fmt="%.1f")

    for ax in axes:
        ax.tick_params(axis="x", rotation=15)

    plt.suptitle("Compress & Compare — Model Variants", fontsize=14)
    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, "comparison_bars.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


def print_summary(benchmarks: list[dict]):
    """Print a text summary table."""
    if not benchmarks:
        return

    print("\n  Summary:")
    print(f"  {'Variant':<20} {'Throughput':>12} {'Latency (ms)':>14} {'VRAM (GB)':>12}")
    print("  " + "-" * 60)
    for b in benchmarks:
        print(
            f"  {b['variant']:<20} "
            f"{b['throughput_tps']:>10.1f} "
            f"{b['latency_median_ms']:>12.0f} "
            f"{b['gpu_memory_mb']/1024:>10.1f}"
        )

    # Speedup relative to original
    original = next((b for b in benchmarks if b["variant"] == "original"), None)
    if original:
        print()
        for b in benchmarks:
            if b["variant"] != "original":
                speedup = b["throughput_tps"] / original["throughput_tps"]
                vram_saving = (1 - b["gpu_memory_mb"] / original["gpu_memory_mb"]) * 100
                print(f"  {b['variant']}: {speedup:.2f}x throughput, {vram_saving:.0f}% VRAM saved")


def main():
    os.makedirs(CHARTS_DIR, exist_ok=True)

    print("Generating trade-off charts...")
    benchmarks = load_benchmarks()

    if not benchmarks:
        print("  No benchmark data found in results/")
        print("  Run 'bash benchmark_all.sh' first.")
        return

    plot_throughput_vs_vram(benchmarks)
    plot_comparison_bars(benchmarks)
    print_summary(benchmarks)

    print(f"\nCharts saved to: {CHARTS_DIR}")


if __name__ == "__main__":
    main()
