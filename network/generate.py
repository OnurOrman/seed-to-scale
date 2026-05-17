import json
import networkx as nx
import os
import pandas as pd
import sys

from dotenv import load_dotenv
from pathlib import Path

from helpers.constants import *
from helpers.json import load_json
from helpers.logging import configure_logging, get_logger
from helpers.string import csv_names_for_vc, deturkify, extract_unique_names, is_name_in, json_names_for_vc

logger = get_logger(__name__)

# Universal layering for bipartite graphs in Gephi
# Layer 0: VC Firms
# Layer 1: Companies
# Layer 2: People (Cofounders, Investment Managers, Employees)
# Layer 3: Institutions (Universities, Past Companies)

# VC firm-Company network
  # Nodes: Companies
    # VC firms: Only 212 for the course project
    # Companies
  # Links: Undirected, unweighted
def vc_company_network(portfolio_csvs: dict[str, str], overwrite: bool = False):
  network_gexf_path = Path(GEPHI_PATH) / "vc_company.gexf"
  if network_gexf_path.exists() and not overwrite:
    logger.info("GEXF already exists: %s", str(network_gexf_path))
    return

  logger.debug("Portfolio CSVs: %s", portfolio_csvs)
  logger.info("Generating VC-Company network...")
  network = nx.Graph()
  
  # Set node type for VCs
  for vc in portfolio_csvs.keys():
    network.add_node(vc, bipartite = 0, type = "VC", label = vc)

  for vc in portfolio_csvs:
    portfolio_csv_path = Path(CSV_PATH) / portfolio_csvs[vc]
    logger.debug("Processing portfolio for VC: %s from %s", vc, portfolio_csv_path)
    portfolio_df = pd.read_csv(portfolio_csv_path)
    logger.debug("Loaded %d portfolio rows for VC: %s", len(portfolio_df), vc)
    
    for _, row in portfolio_df.iterrows():
      company_name = row["company_name"]
      
      # Add startup node with attributes
      attrs = {
        "bipartite": 1,
        "type": "Company",
        "label": company_name
      }

      network.add_node(company_name, **attrs)
      network.add_edge(vc, company_name)
      
    logger.info("Added %d companies for VC: %s", len(portfolio_df), vc)
  
  nx.write_gexf(network, network_gexf_path)
  logger.info(
    "VC-Company network nodes=%d edges=%d",
    network.number_of_nodes(),
    network.number_of_edges(),
  )
  logger.info("VC-Company network saved to: %s", network_gexf_path)

def company_cofounder_network(cofounder_inv_manager_csvs: dict[str, str], overwrite: bool = False):
  network_gexf_path = Path(GEPHI_PATH) / COMPANY_COFOUNDER_GEPHI
  if network_gexf_path.exists() and not overwrite:
    logger.info("GEXF already exists: %s", str(network_gexf_path))
    return
  
  logger.debug("Cofounder CSVs: %s", cofounder_inv_manager_csvs)
  logger.info("Generating Company-Cofounder network...")
  network = nx.Graph()

  for cofounder_inv_manager_csv in cofounder_inv_manager_csvs.values():
    cofounder_inv_manager_path = Path(CSV_PATH) / cofounder_inv_manager_csv
    logger.debug("Processing cofounder file: %s", cofounder_inv_manager_path)
    cofounder_inv_manager_df = pd.read_csv(cofounder_inv_manager_path)
    logger.debug("Loaded %d rows from %s", len(cofounder_inv_manager_df), cofounder_inv_manager_csv)
    
    for _, row in cofounder_inv_manager_df.iterrows():
      if row["cofounder_count"] > 0:
        company = row["company_name"]
        if not network.has_node(company):
          attrs = {
            "bipartite": 1,
            "type": "Company",
            "label": company
          }
          network.add_node(company, **attrs)

        cofounders = extract_unique_names([row["cofounders_name"]])
        for cofounder in cofounders:
          if not network.has_node(cofounder):
            attrs = {
              "bipartite": 2,
              "type": "Cofounder",
              "label": cofounder
            }
            network.add_node(cofounder, **attrs)

          if not network.has_edge(company, cofounder):
            network.add_edge(company, cofounder)
  
  nx.write_gexf(network, network_gexf_path)
  logger.info(
    "Company-Cofounder network nodes=%d edges=%d",
    network.number_of_nodes(),
    network.number_of_edges(),
  )
  logger.info("Company-Cofounder network saved to: %s", network_gexf_path)

def company_inv_manager_network(cofounder_inv_manager_csvs: dict[str, str], overwrite: bool = False):
  network_gexf_path = Path(GEPHI_PATH) / COMPANY_INV_MANAGER_GEPHI
  if network_gexf_path.exists() and not overwrite:
    logger.info("GEXF already exists: %s", str(network_gexf_path))
    return
  
  logger.debug("Investment manager CSVs: %s", cofounder_inv_manager_csvs)
  logger.info("Generating Company-Investment Manager network...")
  network = nx.Graph()

  for cofounder_inv_manager_csv in cofounder_inv_manager_csvs.values():
    cofounder_inv_manager_path = Path(CSV_PATH) / cofounder_inv_manager_csv
    logger.debug("Processing investment manager file: %s", cofounder_inv_manager_path)
    cofounder_inv_manager_df = pd.read_csv(cofounder_inv_manager_path)
    logger.debug("Loaded %d rows from %s", len(cofounder_inv_manager_df), cofounder_inv_manager_csv)
    
    for _, row in cofounder_inv_manager_df.iterrows():
      if row["investment_manager_count"] > 0:
        company = row["company_name"]
        if not network.has_node(company):
          attrs = {
            "bipartite": 1,
            "type": "Company",
            "label": company
          }
          network.add_node(company, **attrs)

        inv_managers = extract_unique_names([row["investment_managers"]])
        for inv_manager in inv_managers:
          if not network.has_node(inv_manager):
            attrs = {
              "bipartite": 2,
              "type": "Investment Manager",
              "label": inv_manager
            }
            network.add_node(inv_manager, **attrs)

          if not network.has_edge(company, inv_manager):
            network.add_edge(company, inv_manager)
  
  nx.write_gexf(network, network_gexf_path)
  logger.info(
    "Company-Investment Manager network nodes=%d edges=%d",
    network.number_of_nodes(),
    network.number_of_edges(),
  )
  logger.info("Company-Investment Manager network saved to: %s", network_gexf_path)

def cofounder_education_network(cofounder_education_jsons: dict[str, str], overwrite: bool = False):
  network_gexf_path = Path(GEPHI_PATH) / COFOUNDER_EDU_GEPHI
  if network_gexf_path.exists() and not overwrite:
    logger.info("GEXF already exists: %s", str(network_gexf_path))
    return
  
  network = nx.Graph()
  for cofounder_education_json in cofounder_education_jsons.values():
    cofounder_education_data = load_json(cofounder_education_json)

    for name, info_cells in cofounder_education_data.items():
      if not network.has_node(name):
        attrs = {
          "bipartite": 2,
          "type": "Cofounder",
          "label": name
        }
        network.add_node(name, **attrs)
      
      for info_cell in info_cells:
        institution = info_cell["school"]

        if not network.has_node(institution):
          attrs = {
            "bipartite": 3,
            "type": "Education",
            "label": institution
          }
          network.add_node(institution, **attrs)
        
        if not network.has_edge(name, institution):
          network.add_edge(name, institution)

  nx.write_gexf(network, network_gexf_path)
  logger.info(
    "Cofounder-Education network nodes=%d edges=%d",
    network.number_of_nodes(),
    network.number_of_edges(),
  )
  logger.info("Cofounder-Education network saved to: %s", network_gexf_path)

def cofounder_experience_network(cofounder_experience_jsons: dict[str, str], overwrite: bool = False):
  network_gexf_path = Path(GEPHI_PATH) / COFOUNDER_EXP_GEPHI
  if network_gexf_path.exists() and not overwrite:
    logger.info("GEXF already exists: %s", str(network_gexf_path))
    return
  
  network = nx.Graph()
  for cofounder_experience_json in cofounder_experience_jsons.values():
    cofounder_experience_data = load_json(cofounder_experience_json)

    for name, info_cells in cofounder_experience_data.items():
      if not network.has_node(name):
        attrs = {
          "bipartite": 2,
          "type": "Cofounder",
          "label": name
        }
        network.add_node(name, **attrs)
      
      for info_cell in info_cells:
        institution = info_cell["company"]

        if not network.has_node(institution):
          attrs = {
            "bipartite": 3,
            "type": "Former Company",
            "label": institution
          }
          network.add_node(institution, **attrs)
        
        if not network.has_edge(name, institution):
          network.add_edge(name, institution)

  nx.write_gexf(network, network_gexf_path)
  logger.info(
    "Cofounder-Experience network nodes=%d edges=%d",
    network.number_of_nodes(),
    network.number_of_edges(),
  )
  logger.info("Cofounder-Experience network saved to: %s", network_gexf_path)

def cofounder_volunteering_network(cofounder_volunteering_jsons: dict[str, str], overwrite: bool = False):
  network_gexf_path = Path(GEPHI_PATH) / COFOUNDER_VOL_GEPHI
  if network_gexf_path.exists() and not overwrite:
    logger.info("GEXF already exists: %s", str(network_gexf_path))
    return

  network = nx.Graph()
  for cofounder_volunteering_json in cofounder_volunteering_jsons.values():
    cofounder_volunteering_data = load_json(cofounder_volunteering_json)

    for name, info_cells in cofounder_volunteering_data.items():
      if not network.has_node(name):
        attrs = {
          "bipartite": 2,
          "type": "Cofounder",
          "label": name
        }
        network.add_node(name, **attrs)
      
      for info_cell in info_cells:
        institution = info_cell["organization"]

        if not network.has_node(institution):
          attrs = {
            "bipartite": 3,
            "type": "Volunteering Organization",
            "label": institution
          }
          network.add_node(institution, **attrs)
        
        if not network.has_edge(name, institution):
          network.add_edge(name, institution)

  nx.write_gexf(network, network_gexf_path)
  logger.info(
    "Cofounder-Volunteering Experience network nodes=%d edges=%d",
    network.number_of_nodes(),
    network.number_of_edges(),
  )
  logger.info("Cofounder-Volunteering Experience network saved to: %s", network_gexf_path)

def inv_manager_education_network(inv_manager_education_jsons: dict[str, str], overwrite: bool = False):
  network_gexf_path = Path(GEPHI_PATH) / EMPLOYEE_EDU_GEPHI
  if network_gexf_path.exists() and not overwrite:
    logger.info("GEXF already exists: %s", str(network_gexf_path))
    return

  network = nx.Graph()
  for inv_manager_education_json in inv_manager_education_jsons.values():
    inv_manager_education_data = load_json(inv_manager_education_json)

    for name, info_cells in inv_manager_education_data.items():
      if not network.has_node(name):
        attrs = {
          "bipartite": 2,
          "type": "Investment Manager",
          "label": name
        }
        network.add_node(name, **attrs)
      
      for info_cell in info_cells:
        institution = info_cell["school"]

        if not network.has_node(institution):
          attrs = {
            "bipartite": 3,
            "type": "Education",
            "label": institution
          }
          network.add_node(institution, **attrs)
        
        if not network.has_edge(name, institution):
          network.add_edge(name, institution)

  nx.write_gexf(network, network_gexf_path)
  logger.info(
    "Investment Manager-Education network nodes=%d edges=%d",
    network.number_of_nodes(),
    network.number_of_edges(),
  )
  logger.info("Investment Manager-Education network saved to: %s", network_gexf_path)

def inv_manager_experience_network(inv_manager_experience_jsons: dict[str, str], overwrite: bool = False):
  network_gexf_path = Path(GEPHI_PATH) / EMPLOYEE_EXP_GEPHI
  if network_gexf_path.exists() and not overwrite:
    logger.info("GEXF already exists: %s", str(network_gexf_path))
    return

  network = nx.Graph()
  for inv_manager_experience_json in inv_manager_experience_jsons.values():
    inv_manager_experience_data = load_json(inv_manager_experience_json)

    for name, info_cells in inv_manager_experience_data.items():
      if not network.has_node(name):
        attrs = {
          "bipartite": 2,
          "type": "Investment Manager",
          "label": name
        }
        network.add_node(name, **attrs)
      
      for info_cell in info_cells:
        institution = info_cell["company"]

        if not network.has_node(institution):
          attrs = {
            "bipartite": 3,
            "type": "Former Company",
            "label": institution
          }
          network.add_node(institution, **attrs)
        
        if not network.has_edge(name, institution):
          network.add_edge(name, institution)

  nx.write_gexf(network, network_gexf_path)
  logger.info(
    "Investment Manager-Experience network nodes=%d edges=%d",
    network.number_of_nodes(),
    network.number_of_edges(),
  )
  logger.info("Investment Manager-Experience network saved to: %s", network_gexf_path)

def inv_manager_volunteering_network(inv_manager_volunteering_jsons: dict[str, str], overwrite: bool = False):
  network_gexf_path = Path(GEPHI_PATH) / EMPLOYEE_VOL_GEPHI
  if network_gexf_path.exists() and not overwrite:
    logger.info("GEXF already exists: %s", str(network_gexf_path))
    return

  network = nx.Graph()
  for inv_manager_volunteering_json in inv_manager_volunteering_jsons.values():
    inv_manager_volunteering_data = load_json(inv_manager_volunteering_json)

    for name, info_cells in inv_manager_volunteering_data.items():
      if not network.has_node(name):
        attrs = {
          "bipartite": 2,
          "type": "Investment Manager",
          "label": name
        }
        network.add_node(name, **attrs)
      
      for info_cell in info_cells:
        institution = info_cell["organization"]

        if not network.has_node(institution):
          attrs = {
            "bipartite": 3,
            "type": "Volunteering Organization",
            "label": institution
          }
          network.add_node(institution, **attrs)
        
        if not network.has_edge(name, institution):
          network.add_edge(name, institution)

  nx.write_gexf(network, network_gexf_path)
  logger.info(
    "Investment Manager-Volunteering Experience network nodes=%d edges=%d",
    network.number_of_nodes(),
    network.number_of_edges(),
  )
  logger.info("Investment Manager-Volunteering Experience network saved to: %s", network_gexf_path)

def cofounder_inv_manager_network(
    cofounder_inv_manager_csvs: dict[str, str],
    cofounder_education_jsons: dict[str, str],
    inv_manager_education_jsons: dict[str, str],
    cofounder_experience_jsons: dict[str, str],
    inv_manager_experience_jsons: dict[str, str],
    cofounder_volunteering_jsons: dict[str, str],
    inv_manager_volunteering_jsons: dict[str, str],
    overwrite: bool = False
  ):
  # Nodes: Cofounder, Investment manager
  # Layer 1:
    # Edges: Cofounder founded a company; investment manager was responsible for the investment in the company
  # Layer 2:
    # Edges: A shared college or high school
  # Layer 3:
    # Edges: A common company for work experience
  # Relationship encoding:
    # Edge attribute `layers`: pipe-delimited list of relationship types.
    # Edge attribute `weight`: count of distinct relationships accumulated per pair.
    # Edge attributes `investment`, `education`, `experience`, `volunteering`:
      # pipe-delimited list of the shared institutions or companies for that layer.
    # Edge attribute `label`: human-readable summary of shared institutions per layer.
  network_gexf_path = Path(GEPHI_PATH) / COFOUNDER_EMPLOYEE_GEPHI
  if network_gexf_path.exists() and not overwrite:
    logger.info("GEXF already exists: %s", str(network_gexf_path))
    return

  logger.info("Generating Cofounder-Investment Manager multilayer network...")
  network = nx.Graph()

  def normalize_person_name(name: str) -> str:
    return deturkify(name.strip()) if isinstance(name, str) else ""

  def normalize_institution_name(name: str) -> str:
    return deturkify(name.strip()) if isinstance(name, str) else ""

  def ensure_person_node(name: str, person_type: str):
    if not name:
      return

    if not network.has_node(name):
      attrs = {
        "bipartite": 2,
        "type": person_type,
        "label": name
      }
      network.add_node(name, **attrs)

  def resolve_person_name(name: str, person_type: str) -> str:
    if not name:
      return ""

    matches = []
    for existing in network.nodes:
      if network.nodes[existing].get("type") != person_type:
        continue
      if is_name_in(name, existing) or is_name_in(existing, name):
        matches.append(existing)

    if not matches:
      return name

    canonical = max([name] + matches, key = len)

    if canonical not in network.nodes:
      existing = matches[0]
      _merge_person_nodes(existing, canonical)
      matches = matches[1:]

    for existing in matches:
      if existing != canonical:
        _merge_person_nodes(existing, canonical)

    return canonical

  def add_layer_edge(name1: str, name2: str, layer: str):
    if not name1 or not name2 or name1 == name2:
      return

    if network.has_edge(name1, name2):
      edge_attrs = network[name1][name2]
      existing_layers = edge_attrs.get("layers", "")
      layers = set(existing_layers.split("|")) if existing_layers else set()
      layers.add(layer)
      edge_attrs["layers"] = "|".join(sorted(layers))
      edge_attrs["weight"] = edge_attrs.get("weight", 1) + 1
    else:
      network.add_edge(name1, name2, layers = layer, weight = 1)

  def add_institution(edge_attrs: dict, layer: str, institution: str | None):
    if not institution:
      return

    existing = edge_attrs.get(layer, "")
    institutions = set(existing.split("|")) if existing else set()
    institutions.add(institution)
    edge_attrs[layer] = "|".join(sorted(institutions))

  def update_edge_label(edge_attrs: dict):
    label_parts = []
    for layer_key in ("investment", "education", "experience", "volunteering"):
      values = edge_attrs.get(layer_key)
      if values:
        label_parts.append(f"{layer_key}:{values}")
    edge_attrs["label"] = "; ".join(label_parts)

  def merge_edge_attrs(target_attrs: dict, source_attrs: dict):
    layer_keys = ("investment", "education", "experience", "volunteering")
    target_attrs["weight"] = target_attrs.get("weight", 1) + source_attrs.get("weight", 1)

    target_layers = set(target_attrs.get("layers", "").split("|")) if target_attrs.get("layers") else set()
    source_layers = set(source_attrs.get("layers", "").split("|")) if source_attrs.get("layers") else set()
    target_attrs["layers"] = "|".join(sorted(target_layers | source_layers))

    for layer_key in layer_keys:
      values = set(target_attrs.get(layer_key, "").split("|")) if target_attrs.get(layer_key) else set()
      values |= set(source_attrs.get(layer_key, "").split("|")) if source_attrs.get(layer_key) else set()
      if values:
        target_attrs[layer_key] = "|".join(sorted(values))

    update_edge_label(target_attrs)

  def _merge_person_nodes(source_name: str, target_name: str):
    if source_name == target_name:
      return

    if target_name not in network.nodes:
      nx.relabel_nodes(network, {source_name: target_name}, copy = False)
      network.nodes[target_name]["label"] = target_name
      return

    for neighbor, edge_attrs in list(network[source_name].items()):
      if neighbor == target_name:
        continue

      if network.has_edge(target_name, neighbor):
        merge_edge_attrs(network[target_name][neighbor], edge_attrs)
      else:
        network.add_edge(target_name, neighbor, **edge_attrs)

    network.remove_node(source_name)
    network.nodes[target_name]["label"] = target_name

  # Layer 1: cofounder-investment manager connections via company
  for cofounder_inv_manager_csv in cofounder_inv_manager_csvs.values():
    cofounder_inv_manager_path = Path(CSV_PATH) / cofounder_inv_manager_csv
    logger.debug("Processing cofounder-investment manager file: %s", cofounder_inv_manager_path)
    cofounder_inv_manager_df = pd.read_csv(cofounder_inv_manager_path)
    logger.debug(
      "Loaded %d rows from %s",
      len(cofounder_inv_manager_df),
      cofounder_inv_manager_csv,
    )

    for _, row in cofounder_inv_manager_df.iterrows():
      if row["cofounder_count"] > 0 and row["investment_manager_count"] > 0:
        cofounders = extract_unique_names([row["cofounders_name"]])
        inv_managers = extract_unique_names([row["investment_managers"]])
        company = normalize_institution_name(row["company_name"])
        for cofounder in cofounders:
          cofounder_name = resolve_person_name(
            normalize_person_name(cofounder),
            "Cofounder",
          )
          ensure_person_node(cofounder_name, "Cofounder")
          for inv_manager in inv_managers:
            inv_manager_name = resolve_person_name(
              normalize_person_name(inv_manager),
              "Investment Manager",
            )
            ensure_person_node(inv_manager_name, "Investment Manager")
            add_layer_edge(cofounder_name, inv_manager_name, "investment")
            edge_attrs = network[cofounder_name][inv_manager_name]
            add_institution(edge_attrs, "investment", company)
            update_edge_label(edge_attrs)

  def build_institution_map(jsons: dict[str, str], key: str) -> dict[str, set[str]]:
    institution_map: dict[str, set[str]] = {}
    for json_file in jsons.values():
      data = load_json(json_file)
      for raw_name, info_cells in data.items():
        person_name = normalize_person_name(raw_name)
        if not person_name:
          continue

        for info_cell in info_cells:
          institution = normalize_institution_name(info_cell.get(key, ""))
          if not institution:
            continue
          institution_map.setdefault(institution, set()).add(person_name)

    return institution_map

  def connect_shared_institutions(
      cofounder_map: dict[str, set[str]],
      inv_manager_map: dict[str, set[str]],
      layer: str,
  ):
    for institution, cofounders in cofounder_map.items():
      inv_managers = inv_manager_map.get(institution)
      if not inv_managers:
        continue

      for cofounder in cofounders:
        cofounder_name = resolve_person_name(cofounder, "Cofounder")
        ensure_person_node(cofounder_name, "Cofounder")
        for inv_manager in inv_managers:
          inv_manager_name = resolve_person_name(inv_manager, "Investment Manager")
          ensure_person_node(inv_manager_name, "Investment Manager")
          add_layer_edge(cofounder_name, inv_manager_name, layer)
          edge_attrs = network[cofounder_name][inv_manager_name]
          add_institution(edge_attrs, layer, institution)
          update_edge_label(edge_attrs)

  # Layer 2: shared education institutions
  cofounder_edu_map = build_institution_map(cofounder_education_jsons, "school")
  inv_manager_edu_map = build_institution_map(inv_manager_education_jsons, "school")
  connect_shared_institutions(cofounder_edu_map, inv_manager_edu_map, "education")

  # Layer 3: shared work experience companies
  cofounder_exp_map = build_institution_map(cofounder_experience_jsons, "company")
  inv_manager_exp_map = build_institution_map(inv_manager_experience_jsons, "company")
  connect_shared_institutions(cofounder_exp_map, inv_manager_exp_map, "experience")

  # Additional layer: shared volunteering organizations
  cofounder_vol_map = build_institution_map(cofounder_volunteering_jsons, "organization")
  inv_manager_vol_map = build_institution_map(inv_manager_volunteering_jsons, "organization")
  connect_shared_institutions(cofounder_vol_map, inv_manager_vol_map, "volunteering")

  nx.write_gexf(network, network_gexf_path)
  logger.info(
    "Cofounder-Investment Manager network nodes=%d edges=%d",
    network.number_of_nodes(),
    network.number_of_edges(),
  )
  logger.info("Cofounder-Investment Manager network saved to: %s", network_gexf_path)

def main(overwrite: bool = False):
  configure_logging()

  vcs = os.getenv("VC").split(",")
  portfolio_csvs = dict(); team_csvs = dict(); cofounder_inv_manager_csvs = dict()
  cofounders_csvs = dict(); cofounders_education_csvs = dict()
  cofounders_experience_csvs = dict(); cofounders_volunteering_csvs = dict()

  investment_managers_csvs = dict(); investment_managers_education_csvs = dict()
  investment_managers_experience_csvs = dict(); investment_managers_volunteering_csvs = dict()

  cofounders_education_jsons = dict(); cofounders_experience_jsons = dict();\
    cofounders_volunteering_jsons = dict()
  investment_managers_education_jsons = dict(); investment_managers_experience_jsons = dict();\
    investment_managers_volunteering_jsons = dict()

  for vc in vcs:
    portfolio_csvs[vc], team_csvs[vc], cofounder_inv_manager_csvs[vc],\
    cofounders_csvs[vc], cofounders_education_csvs[vc],\
    cofounders_experience_csvs[vc], cofounders_volunteering_csvs[vc],\
    investment_managers_csvs[vc], investment_managers_education_csvs[vc],\
    investment_managers_experience_csvs[vc], investment_managers_volunteering_csvs[vc]\
    = csv_names_for_vc(vc)

    cofounders_education_jsons[vc], cofounders_experience_jsons[vc],\
    cofounders_volunteering_jsons[vc], investment_managers_education_jsons[vc],\
    investment_managers_experience_jsons[vc], investment_managers_volunteering_jsons[vc]\
    = json_names_for_vc(vc)
  
  vc_company_network(portfolio_csvs, overwrite)
  company_cofounder_network(cofounder_inv_manager_csvs, overwrite)
  company_inv_manager_network(cofounder_inv_manager_csvs, overwrite)

  cofounder_education_network(cofounders_education_jsons, overwrite)
  cofounder_experience_network(cofounders_experience_jsons, overwrite)
  cofounder_volunteering_network(cofounders_volunteering_jsons, overwrite)

  inv_manager_education_network(investment_managers_education_jsons, overwrite)
  inv_manager_experience_network(investment_managers_experience_jsons, overwrite)
  inv_manager_volunteering_network(investment_managers_volunteering_jsons, overwrite)

  cofounder_inv_manager_network(
    cofounder_inv_manager_csvs,
    cofounders_education_jsons,
    investment_managers_education_jsons,
    cofounders_experience_jsons,
    investment_managers_experience_jsons,
    cofounders_volunteering_jsons,
    investment_managers_volunteering_jsons,
    overwrite,
  )

if __name__ == "__main__":
  load_dotenv()
  args = [arg for arg in sys.argv[1:] if arg != "--overwrite"]
  overwrite_flag = "--overwrite" in sys.argv

  if len(args) != 0:
    logger.error("Usage: uv run -m network.generate [--overwrite]")
    exit(os.EX_USAGE)

  main(overwrite = overwrite_flag)

