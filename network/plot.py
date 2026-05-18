import json
import math
from pathlib import Path

import matplotlib.pyplot as plt

from helpers.constants import *

DATA_RESULTS_DIR = Path(RESULTS_PATH)
FIGURES_DIR = Path(FIGURES_PATH)

PALETTE = {
  "primary": "#0D1B2A",
  "accent": "#1B7F8E",
  "background": "#D4EEF2",
  "highlight": "#E8A838",
  "panel": "#F2F4F7",
  "caption": "#8A9BB0",
}


def load_json(path: Path) -> dict:
  with path.open("r", encoding="utf-8") as handle:
    return json.load(handle)


def latest_results_dir() -> Path:
  if not DATA_RESULTS_DIR.exists():
    raise FileNotFoundError(f"Missing results directory: {DATA_RESULTS_DIR}")

  candidates = [p for p in DATA_RESULTS_DIR.iterdir() if p.is_dir()]
  if not candidates:
    raise FileNotFoundError("No results runs found in data/results")

  return sorted(candidates, key=lambda p: p.name)[-1]


def ensure_figures_dir() -> Path:
  FIGURES_DIR.mkdir(parents=True, exist_ok=True)
  return FIGURES_DIR


def setup_style():
  plt.rcParams.update(
    {
      "font.family": "sans-serif",
      "font.sans-serif": ["Helvetica", "Inter", "Arial", "DejaVu Sans"],
      "figure.facecolor": PALETTE["background"],
      "axes.facecolor": PALETTE["panel"],
      "axes.edgecolor": PALETTE["caption"],
      "axes.labelcolor": PALETTE["primary"],
      "axes.titlecolor": PALETTE["primary"],
      "xtick.color": PALETTE["primary"],
      "ytick.color": PALETTE["primary"],
      "grid.color": PALETTE["caption"],
      "text.color": PALETTE["primary"],
      "font.size": 11,
    }
  )


def plot_network_sizes(stats_files: list[Path], output_dir: Path):
  labels = []
  nodes = []
  edges = []

  for path in stats_files:
    data = load_json(path)
    labels.append(path.stem.replace("_network_stats", ""))
    nodes.append(data.get("nodes", 0))
    edges.append(data.get("edges", 0))

  x = range(len(labels))
  width = 0.35

  fig, ax = plt.subplots(figsize=(10, 5))
  ax.bar([i - width / 2 for i in x], nodes, width, label="Nodes", color=PALETTE["accent"])
  ax.bar([i + width / 2 for i in x], edges, width, label="Edges", color=PALETTE["highlight"])

  ax.set_title("Network Size by Graph")
  ax.set_xlabel("Network")
  ax.set_ylabel("Count")
  ax.set_xticks(list(x))
  ax.set_xticklabels(labels, rotation=30, ha="right")
  ax.grid(axis="y", linestyle="--", alpha=0.4)
  ax.legend()

  fig.tight_layout()
  fig.savefig(output_dir / "network_sizes.png", dpi=300)
  plt.close(fig)


def plot_modularity(community_path: Path, output_dir: Path):
  data = load_json(community_path)
  algorithms = []
  modularity = []

  for entry in data.get("algorithms", []):
    result = entry.get("result")
    if result is None:
      continue
    algorithms.append(entry.get("name", "unknown"))
    modularity.append(result.get("modularity", 0))

  fig, ax = plt.subplots(figsize=(8, 5))
  ax.bar(algorithms, modularity, color=PALETTE["accent"])
  ax.set_title("Community Detection Modularity")
  ax.set_xlabel("Algorithm")
  ax.set_ylabel("Modularity (Q)")
  ax.set_ylim(0, max(modularity) * 1.2 if modularity else 1)
  ax.grid(axis="y", linestyle="--", alpha=0.4)

  fig.tight_layout()
  fig.savefig(output_dir / "community_modularity.png", dpi=300)
  plt.close(fig)


def select_algorithm_results(data: dict) -> dict[str, dict]:
  best_by_name: dict[str, dict] = {}

  for entry in data.get("algorithms", []):
    name = entry.get("name", "unknown")
    result = entry.get("result")
    if result is None:
      continue
    modularity = result.get("modularity", 0)

    if name not in best_by_name or modularity > best_by_name[name]["modularity"]:
      best_by_name[name] = {
        "modularity": modularity,
        "title": result.get("title", name),
        "communities": result.get("communities", []),
      }

  return best_by_name


def plot_community_sizes(community_path: Path, output_dir: Path):
  data = load_json(community_path)
  best = select_algorithm_results(data)
  if not best:
    return

  algorithms = list(best.keys())
  n = len(algorithms)
  cols = 2
  rows = math.ceil(n / cols)

  fig, axes = plt.subplots(rows, cols, figsize=(10, 4 * rows))
  axes = axes.flatten() if isinstance(axes, (list, tuple)) is False else axes

  for idx, name in enumerate(algorithms):
    ax = axes[idx]
    communities = best[name]["communities"]
    sizes = sorted([c.get("size", 0) for c in communities], reverse=True)
    labels = [f"C{i+1}" for i in range(len(sizes))]

    ax.bar(labels, sizes, color=PALETTE["accent"])
    ax.set_title(f"{name} (Q={best[name]['modularity']:.3f})")
    ax.set_xlabel("Community")
    ax.set_ylabel("Size")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

  for j in range(idx + 1, len(axes)):
    axes[j].axis("off")

  fig.tight_layout()
  fig.savefig(output_dir / "community_size_distributions.png", dpi=300)
  plt.close(fig)


def plot_top_degree(stats_path: Path, output_dir: Path, top_n: int = 10):
  data = load_json(stats_path)
  top_degree = data.get("centrality_top10", {}).get("degree", [])[:top_n]

  labels = [entry["node"] for entry in top_degree]
  scores = [entry["score"] for entry in top_degree]

  fig, ax = plt.subplots(figsize=(8, 6))
  ax.barh(labels[::-1], scores[::-1], color=PALETTE["highlight"])
  ax.set_title("Top Degree Centrality (Cofounder-Investment Manager)")
  ax.set_xlabel("Degree Centrality")
  ax.set_ylabel("Person")
  ax.grid(axis="x", linestyle="--", alpha=0.4)

  fig.tight_layout()
  fig.savefig(output_dir / "top_degree_centrality.png", dpi=300)
  plt.close(fig)


def plot_centrality_comparison(stats_path: Path, output_dir: Path, top_n: int = 10):
  data = load_json(stats_path)
  centrality = data.get("centrality_top10", {})
  degree = centrality.get("degree", [])[:top_n]

  nodes = [entry["node"] for entry in degree]

  def score_map(metric: str) -> dict[str, float]:
    return {entry["node"]: entry["score"] for entry in centrality.get(metric, [])}

  betweenness = score_map("betweenness")
  closeness = score_map("closeness")
  eigenvector = score_map("eigenvector")
  pagerank = score_map("pagerank")

  metrics = [
    ("degree", score_map("degree"), PALETTE["primary"]),
    ("betweenness", betweenness, PALETTE["accent"]),
    ("closeness", closeness, PALETTE["highlight"]),
    ("eigenvector", eigenvector, PALETTE["caption"]),
    ("pagerank", pagerank, PALETTE["panel"]),
  ]

  x = range(len(nodes))
  width = 0.15

  fig, ax = plt.subplots(figsize=(12, 5))
  for idx, (label, mapping, color) in enumerate(metrics):
    values = [mapping.get(node, 0) for node in nodes]
    offset = (idx - 2) * width
    ax.bar([i + offset for i in x], values, width, label=label, color=color)

  ax.set_title("Centrality Comparison (Top Degree Nodes)")
  ax.set_xlabel("Node")
  ax.set_ylabel("Score")
  ax.set_xticks(list(x))
  ax.set_xticklabels(nodes, rotation=30, ha="right")
  ax.grid(axis="y", linestyle="--", alpha=0.4)
  ax.legend()

  fig.tight_layout()
  fig.savefig(output_dir / "centrality_comparison.png", dpi=300)
  plt.close(fig)


def plot_density_assortativity(stats_path: Path, output_dir: Path):
  data = load_json(stats_path)
  density = data.get("density", 0)
  assortativity = data.get("assortativity_degree")

  fig, ax = plt.subplots(figsize=(6, 4))
  values = [density, assortativity if assortativity is not None else 0]
  labels = ["Density", "Assortativity"]

  ax.bar(labels, values, color=[PALETTE["accent"], PALETTE["highlight"]])
  ax.set_title("Connectivity Metrics")
  ax.set_xlabel("Metric")
  ax.set_ylabel("Value")
  ax.axhline(0, color=PALETTE["caption"], linewidth=1)
  ax.grid(axis="y", linestyle="--", alpha=0.4)

  fig.tight_layout()
  fig.savefig(output_dir / "connectivity_metrics.png", dpi=300)
  plt.close(fig)


def main():
  setup_style()
  output_dir = ensure_figures_dir()
  results_dir = latest_results_dir()

  stats_files = sorted(results_dir.glob("*_network_stats.json"))
  community_files = sorted(results_dir.glob("*_community_detection.json"))

  if not stats_files:
    raise FileNotFoundError(f"No network_stats.json files found in {results_dir}")

  plot_network_sizes(stats_files, output_dir)

  if community_files:
    plot_modularity(community_files[0], output_dir)
    plot_community_sizes(community_files[0], output_dir)

  cofounder_stats = results_dir / "cofounders_employee_network_stats.json"
  if cofounder_stats.exists():
    plot_top_degree(cofounder_stats, output_dir)
    plot_density_assortativity(cofounder_stats, output_dir)
    plot_centrality_comparison(cofounder_stats, output_dir)

  print(f"Figures saved to: {output_dir.name}")


if __name__ == "__main__":
  main()
