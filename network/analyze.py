import json
import networkx as nx
import os
import sys

from collections import Counter
from pathlib import Path

from helpers.constants import COFOUNDER_EMPLOYEE_GEPHI, COMMUNITY_DETECTION_JSON, GEPHI_PATH, NETWORK_STATS_JSON, RESULTS_PATH
from helpers.logging import configure_logging, get_logger
from helpers.string import is_name_in
from helpers.run import current_run_info

logger = get_logger(__name__)

LAYER_KEYS = ("investment", "education", "experience", "volunteering")

def _serialize_communities(
	title: str,
	communities: list[set[str]],
	modularity: float | None,
	graph: nx.Graph,
	top_n: int = 8,
):
	# Serialize communities with shared-attribute summaries for export.
	payload = {
		"title": title,
		"modularity": modularity,
		"communities": [],
	}

	for idx, community in enumerate(communities, start = 1):
		members = sorted(community)
		deduped = _dedupe_members(graph, members)
		shared = _collect_shared_attributes(graph, set(community), top_n)
		payload["communities"].append({
			"id": idx,
			"size": len(members),
			"deduped_size": sum(len(values) for values in deduped.values()),
			"members": {
				"cofounders": deduped.get("Cofounder", []),
				"investment_managers": deduped.get("Investment Manager", []),
				"other": deduped.get("Other", []),
			},
			"shared": shared,
		})

	return payload

def _dedupe_members(graph: nx.Graph, members: list[str]) -> dict[str, list[str]]:
	# Group by node type and dedupe within each group using fuzzy containment.
	grouped = {
		"Cofounder": [],
		"Investment Manager": [],
		"Other": [],
	}

	for name in members:
		node_type = graph.nodes[name].get("type", "Other")
		group_key = node_type if node_type in grouped else "Other"
		grouped[group_key].append(name)

	for group_key, names in grouped.items():
		grouped[group_key] = _dedupe_group(names)

	return grouped

def _dedupe_group(names: list[str]) -> list[str]:
	if len(names) <= 1:
		return names

	ordered = sorted(names, key = len, reverse = True)
	kept: list[str] = []

	for candidate in ordered:
		# Skip shorter variants when an overlapping longer name exists.
		if any(is_name_in(candidate, existing) or is_name_in(existing, candidate) for existing in kept):
			continue
		kept.append(candidate)

	return sorted(kept)

def _collect_shared_values(edge_attrs: dict, layer_key: str) -> list[str]:
	# Each layer attribute is a pipe-delimited list of institutions.
	raw = edge_attrs.get(layer_key)
	if not raw:
		return []
	return [value for value in raw.split("|") if value]

def _collect_shared_attributes(graph: nx.Graph, community: set[str], top_n: int) -> dict[str, list[dict[str, int]]]:
	# Aggregate shared institutions/companies across all edges in the community.
	counters = {layer: Counter() for layer in LAYER_KEYS}

	subgraph = graph.subgraph(community)
	for _, _, edge_attrs in subgraph.edges(data = True):
		for layer_key in LAYER_KEYS:
			for value in _collect_shared_values(edge_attrs, layer_key):
				counters[layer_key][value] += 1

	summary: dict[str, list[dict[str, int]]] = {}
	for layer_key in LAYER_KEYS:
		if not counters[layer_key]:
			continue
		top_items = counters[layer_key].most_common(top_n)
		summary[layer_key] = [{"name": name, "count": count} for name, count in top_items]

	return summary

def _describe_network(gexf_path: Path) -> dict:
	if not gexf_path.exists():
		raise FileNotFoundError(f"GEXF not found: {gexf_path}")
	
	graph: nx.Graph = nx.read_gexf(gexf_path)

	# Basic descriptive statistics for any NetworkX graph.
	if graph.number_of_nodes() == 0:
		return {
			"gexf_path": str(gexf_path),
			"nodes": 0,
			"edges": 0
		}
	
	is_directed = graph.is_directed()
	components = list(nx.weakly_connected_components(graph)) if is_directed else list(nx.connected_components(graph))
	component_sizes = sorted((len(c) for c in components), reverse = True)
	degree_values = [degree for _, degree in graph.degree()]
	largest_component_nodes = max(components, key = len) if components else set()
	largest_component = graph.subgraph(largest_component_nodes).copy() if largest_component_nodes else graph

	def top_k(centrality: dict[str, float], k: int = 10) -> list[dict[str, float]]:
		items = sorted(centrality.items(), key = lambda item: item[1], reverse = True)[:k]
		return [{"node": node, "score": score} for node, score in items]

	def weighted_degree_centrality(g: nx.Graph) -> dict[str, float]:
		if g.number_of_nodes() <= 1:
			return {node: 0 for node in g.nodes}
			norm = 1
		else:
			norm = g.number_of_nodes() - 1
		return {node: (degree / norm) for node, degree in g.degree(weight = "weight")}

	centrality = {
		"degree": {},
		"degree_weighted": {},
		"betweenness": {},
		"betweenness_weighted": {},
		"closeness": {},
		"closeness_weighted": {},
		"eigenvector": {},
		"eigenvector_weighted": {},
		"pagerank": {},
		"pagerank_weighted": {},
	}

	centrality["degree"] = top_k(nx.degree_centrality(graph))
	centrality["degree_weighted"] = top_k(weighted_degree_centrality(graph))
	centrality["betweenness"] = top_k(nx.betweenness_centrality(graph))
	centrality["betweenness_weighted"] = top_k(nx.betweenness_centrality(graph, weight = "weight"))
	centrality["closeness"] = top_k(nx.closeness_centrality(graph))
	centrality["closeness_weighted"] = top_k(nx.closeness_centrality(graph, distance = "weight"))

	try:
		centrality["eigenvector"] = top_k(nx.eigenvector_centrality(graph, max_iter = 1000))
		centrality["eigenvector_weighted"] = top_k(
			nx.eigenvector_centrality(graph, max_iter = 1000, weight = "weight")
		)
	except nx.PowerIterationFailedConvergence:
		centrality["eigenvector"] = []
		centrality["eigenvector_weighted"] = []

	centrality["pagerank"] = top_k(nx.pagerank(graph))
	centrality["pagerank_weighted"] = top_k(nx.pagerank(graph, weight = "weight"))

	try:
		diameter = nx.diameter(largest_component) if largest_component.number_of_nodes() > 0 else None
		avg_shortest_path = nx.average_shortest_path_length(largest_component) if largest_component.number_of_nodes() > 0 else None
	except nx.NetworkXError:
		diameter = None
		avg_shortest_path = None

	assortativity = nx.degree_assortativity_coefficient(graph) if graph.number_of_nodes() > 1 else None

	stats = {
		"gexf_path": str(gexf_path),
		"nodes": graph.number_of_nodes(),
		"edges": graph.number_of_edges(),
		"directed": is_directed,
		"density": nx.density(graph),
		"avg_degree": sum(degree_values) / len(degree_values) if degree_values else 0,
		"min_degree": min(degree_values) if degree_values else 0,
		"max_degree": max(degree_values) if degree_values else 0,
		"connected_components": {
			"count": len(components),
			"largest_size": component_sizes[0] if component_sizes else 0,
			"sizes": component_sizes,
		},
		"average_clustering": nx.average_clustering(graph) if not is_directed else None,
		"assortativity_degree": assortativity,
		"diameter_largest_component": diameter,
		"avg_shortest_path_largest_component": avg_shortest_path,
		"centrality_top10": centrality,
	}

	return stats

def _run_community_detection(gexf_path: Path, results_dir: Path, run_payload: dict) -> nx.Graph | None:
	logger.info("Loading GEXF from %s", gexf_path)
	if not gexf_path.exists():
		raise FileNotFoundError(f"GEXF not found: {gexf_path}")

	graph = nx.read_gexf(gexf_path)
	if graph.number_of_nodes() == 0:
		print("No nodes found in the graph.")
		return None

	logger.info("Loaded graph: nodes=%d edges=%d", graph.number_of_nodes(), graph.number_of_edges())
	logger.info("Writing results to %s", results_dir)

	run_payload["input"] = {
		"gexf_path": str(gexf_path),
		"nodes": graph.number_of_nodes(),
		"edges": graph.number_of_edges(),
	}
	logger.info(
		"Graph loaded with %d nodes and %d edges",
		graph.number_of_nodes(),
		graph.number_of_edges(),
	)

	louvain_fn = getattr(nx.algorithms.community, "louvain_communities", None)
	if louvain_fn is not None:
		# Louvain: greedy, multi-level modularity optimization that coarsens the
		# graph into communities, then refines by moving nodes to improve modularity.
		# When to use: large graphs where you want fast, high-quality partitions.
		# Parameter tips: use `weight` for edge strength; set `seed` for reproducible
		# results; adjust `resolution` (if available) to favor more/smaller vs fewer
		# larger communities.
		logger.info("Running Louvain community detection")
		louvain_communities = louvain_fn(graph, weight = "weight", seed = 42)
		louvain_modularity = nx.algorithms.community.modularity(
			graph,
			louvain_communities,
			weight = "weight",
		)
		run_payload["algorithms"].append({
			"name": "louvain",
			"parameters": {"weight": "weight", "seed": 42},
			"result": _serialize_communities(
				"Louvain communities",
				list(louvain_communities),
				louvain_modularity,
				graph,
			),
		})
	else:
		run_payload["algorithms"].append({
			"name": "louvain",
			"parameters": {"weight": "weight", "seed": 42},
			"result": None,
			"note": "Unavailable (networkx missing louvain_communities).",
		})

	greedy_communities = list(
		nx.algorithms.community.greedy_modularity_communities(graph, weight = "weight")
	)
	# Greedy modularity: iteratively merges communities that provide the largest
	# modularity gain until no merge improves the score.
	# When to use: small/medium graphs when you want a deterministic baseline.
	# Parameter tips: include `weight` to respect edge strength; for reproducible
	# results keep graph deterministic (ordering affects ties).
	logger.info("Running greedy modularity community detection")
	greedy_modularity = nx.algorithms.community.modularity(
		graph,
		greedy_communities,
		weight = "weight",
	)
	run_payload["algorithms"].append({
		"name": "greedy_modularity",
		"parameters": {"weight": "weight"},
		"result": _serialize_communities(
			"Greedy modularity communities",
			greedy_communities,
			greedy_modularity,
			graph,
		),
	})

	label_prop = list(nx.algorithms.community.label_propagation_communities(graph))
	# Label propagation: initializes each node with a label and repeatedly updates
	# to the most frequent neighbor label until labels stabilize into communities.
	# When to use: very large graphs when you need a fast, lightweight heuristic.
	# Parameter tips: no weights by default in NetworkX; results can vary across
	# runs due to random tie-breaking, so compare multiple runs if needed.
	logger.info("Running label propagation community detection")
	label_prop_modularity = nx.algorithms.community.modularity(
		graph,
		label_prop,
		weight = "weight",
	)
	run_payload["algorithms"].append({
		"name": "label_propagation",
		"parameters": {"weight": "weight"},
		"result": _serialize_communities(
			"Label propagation communities",
			label_prop,
			label_prop_modularity,
			graph,
		),
	})

	girvan_iter = nx.algorithms.community.girvan_newman(graph)
	# Girvan-Newman: edge-betweenness approach that removes bridging edges to split
	# the graph; each split level increases the number of communities.
	# When to use: exploratory analysis on small graphs or when you want hierarchy.
	# Parameter tips: choose how many split levels to explore; deeper splits reveal
	# finer communities but can be expensive.
	max_levels = 3
	for level in range(1, max_levels + 1):
		try:
			logger.info("Running Girvan-Newman split level %d", level)
			partition = next(girvan_iter)
		except StopIteration:
			if level == 1:
				run_payload["algorithms"].append({
					"name": "girvan_newman",
					"parameters": {"level": level},
					"result": None,
					"note": "Unavailable (no split found).",
				})
			break

		girvan_communities = [set(c) for c in partition]
		girvan_modularity = nx.algorithms.community.modularity(
			graph,
			girvan_communities,
			weight = "weight",
		)
		run_payload["algorithms"].append({
			"name": "girvan_newman",
			"parameters": {"level": level, "k": len(girvan_communities)},
			"result": _serialize_communities(
				f"Girvan-Newman communities (split {level}, k={len(girvan_communities)})",
				girvan_communities,
				girvan_modularity,
				graph,
			),
		})

	results_path = results_dir / COMMUNITY_DETECTION_JSON
	with results_path.open("w", encoding = "utf-8") as handle:
		json.dump(run_payload, handle, indent = 2, ensure_ascii = False)

	logger.info("Results saved to %s", results_path)

	return graph

def detect_communities(_run_id = None, _run_ts = None):
	gexf_path = Path(GEPHI_PATH) / COFOUNDER_EMPLOYEE_GEPHI
	if (_run_id is None) and (_run_ts is None):
		run_id, run_ts = current_run_info()
	else:
		run_id = _run_id
		run_ts = _run_ts
	
	results_dir = Path(RESULTS_PATH) / f"{run_ts}_{run_id}"
	results_dir.mkdir(parents = True, exist_ok = True)
	logger.info("Writing results to %s", results_dir)

	run_payload = {
		"run_id": run_id,
		"timestamp_utc": run_ts,
		"input": {},
		"algorithms": [],
	}

	graph = _run_community_detection(gexf_path, results_dir, run_payload)
	if graph is None:
		return

	stats_path = results_dir / NETWORK_STATS_JSON
	with stats_path.open("w", encoding = "utf-8") as handle:
		json.dump(_describe_network(gexf_path), handle, indent = 2, ensure_ascii = False)

	logger.info("Network stats saved to %s", stats_path)

def describe_network(gexf_file: str, run_id, run_ts, overwrite: bool = False):
	gexf_path = Path(GEPHI_PATH) / gexf_file
	results_dir = Path(RESULTS_PATH) / f"{run_ts}_{run_id}"
	results_dir.mkdir(parents = True, exist_ok = True)

	stats_path = results_dir / NETWORK_STATS_JSON

	if stats_path.exists() and not overwrite:
		logger.info("GEXF already exists: %s", str(stats_path))
		return

	with stats_path.open("w", encoding = "utf-8") as handle:
		json.dump(_describe_network(gexf_path), handle, indent = 2, ensure_ascii = False)

	logger.info("Network stats saved to %s", stats_path)

def describe_networks(run_id, run_ts, overwrite: bool = False):
	gexf_dir = Path(GEPHI_PATH)

	for gexf_file in sorted(gexf_dir.glob("*.gexf")):
		describe_network(gexf_file.name, run_id, run_ts, overwrite)

if __name__ == "__main__":
	configure_logging()

	args = [arg for arg in sys.argv[1:] if arg != "--overwrite"]
	overwrite_flag = "--overwrite" in sys.argv
	
	if len(args) != 0:
		logger.error("Usage: uv run -m network.analyze [--overwrite]")
		exit(os.EX_USAGE)

	run_id, run_ts = current_run_info()
	describe_networks(run_id, run_ts, overwrite_flag)
	detect_communities(run_id, run_ts)
