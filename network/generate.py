import networkx as nx
import os
import pandas as pd
import sys

from dotenv import load_dotenv
from pathlib import Path

from helpers.constants import *
from helpers.logging import configure_logging, get_logger
from helpers.string import csv_names_for_vc, extract_unique_names

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

def main(overwrite: bool = False):
  configure_logging()
  load_dotenv()

  vcs = os.getenv("VC").split(",")
  portfolio_csvs = dict(); team_csvs = dict(); cofounder_inv_manager_csvs = dict()
  cofounders_csvs = dict(); cofounders_education_csvs = dict()
  cofounders_experience_csvs = dict(); cofounders_volunteering_csvs = dict()

  investment_managers_csvs = dict(); investment_managers_education_csvs = dict()
  investment_managers_experience_csvs = dict(); investment_managers_volunteering_csvs = dict()

  for vc in vcs:
    portfolio_csvs[vc], team_csvs[vc], cofounder_inv_manager_csvs[vc],\
    cofounders_csvs[vc], cofounders_education_csvs[vc],\
    cofounders_experience_csvs[vc], cofounders_volunteering_csvs[vc],\
    investment_managers_csvs[vc], investment_managers_education_csvs[vc],\
    investment_managers_experience_csvs[vc], investment_managers_volunteering_csvs[vc]\
    = csv_names_for_vc(vc)
  
  vc_company_network(portfolio_csvs, overwrite)
  company_cofounder_network(cofounder_inv_manager_csvs, overwrite)
  company_inv_manager_network(cofounder_inv_manager_csvs, overwrite)

if __name__ == "__main__":
  args = [arg for arg in sys.argv[1:] if arg != "--overwrite"]
  overwrite_flag = "--overwrite" in sys.argv

  if len(args) != 0:
    logger.error("Usage: uv run -m network.generate [--overwrite]")
    exit(os.EX_USAGE)

  main(overwrite = overwrite_flag)

