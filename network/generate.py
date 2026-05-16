import networkx as nx
import pandas as pd

from pathlib import Path

from helpers.constants import *
from helpers.logging import get_logger

logger = get_logger(__name__)

# VC firm-Startup network
  # Nodes: Companies
    # VC firms: Only 212 for the course project
    # Startups
  # Links: Undirected, unweighted
def vc_startup_network(portfolio_csvs: dict[str, str], overwrite: bool = False):
  network_gexf_path = Path(GEPHI_PATH) / "vc_startup.gexf"
  if network_gexf_path.exists() and not overwrite:
    logger.info("GEXF already exists: %s", str(network_gexf_path))
    return

  logger.info("Generating VC-Startup network...")
  network = nx.Graph()
  
  # Set node type for VCs
  for vc in portfolio_csvs.keys():
    network.add_node(vc, bipartite = 0, type = "VC", label = vc)

  for vc in portfolio_csvs:
    portfolio_csv_path = Path(CSV_PATH) / portfolio_csvs[vc]
    logger.debug("Processing portfolio for VC: %s from %s", vc, portfolio_csv_path)
    portfolio_df = pd.read_csv(portfolio_csv_path)
    
    for _, row in portfolio_df.iterrows():
      company_name = row["company_name"]
      
      # Add startup node with attributes
      attrs = {
        "bipartite": 1,
        "type": "Startup",
        "label": company_name
      }

      network.add_node(company_name, **attrs)
      network.add_edge(vc, company_name)
      
    logger.info("Added %d companies for VC: %s", len(portfolio_df), vc)
  
  network_gexf_path = Path(GEPHI_PATH) / "vc_startup.gexf"
  nx.write_gexf(network, network_gexf_path)
  logger.info("VC-Startup network saved to: %s", network_gexf_path)
