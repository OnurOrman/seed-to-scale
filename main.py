import asyncio
import os
import sys

import collect
import network
import scrape

from dotenv import load_dotenv

from helpers.logging import configure_logging, get_logger
from helpers.string import csv_names_for_vc, json_names_for_vc

logger = get_logger(__name__)

def main(overwrite: bool = False, collect_flag: bool = False, scrape_flag: bool = False, network_flag: bool = False):
  logger.info("Starting seed-to-scale run.")
  portfolio_csv = ""
  team_csv = ""

  vcs = os.getenv("VC").split(",")
  vc_linkedins = os.getenv("VC_LINKEDIN").split(",")

  if collect_flag:
    for vc, vc_linkedin in zip(vcs, vc_linkedins):
      if vc == "212":
        portfolio_csv, team_csv = collect.vc_212.main(overwrite = overwrite)
      
      employees_csv = asyncio.run(collect.linkedin.main(
        vc, vc_linkedin, overwrite = overwrite
      ))
      
      investment_manager_json = collect.investment_managers.get_investment_managers(
        collect.investment_managers.collect_investment_managers(
          team_csv,
          employees_csv,
          portfolio_csv,
          overwrite = overwrite,
        )
      )

      asyncio.run(collect.linkedin.vc_investment_managers(
        vc,
        investment_manager_json,
        overwrite = overwrite,
      ))
      
      logger.info("Collected the data for %s", vc)

  if scrape_flag:
    scrape.linkedin.main(overwrite)

  if network_flag:
    portfolio_csvs = dict(); team_csvs = dict(); cofounders_inv_manager_csvs = dict()
    cofounders_csvs = dict(); cofounders_education_csvs = dict()
    cofounders_experience_csvs = dict(); cofounders_volunteering_csvs = dict()

    investment_managers_csvs = dict(); investment_managers_education_csvs = dict()
    investment_managers_experience_csvs = dict(); investment_managers_volunteering_csvs = dict()

    cofounders_education_jsons = dict(); cofounders_experience_jsons = dict();\
      cofounders_volunteering_jsons = dict()
    investment_managers_education_jsons = dict(); investment_managers_experience_jsons = dict();\
      investment_managers_volunteering_jsons = dict()

    for vc in vcs:
      portfolio_csvs[vc], team_csvs[vc], cofounders_inv_manager_csvs[vc],\
      cofounders_csvs[vc], cofounders_education_csvs[vc],\
      cofounders_experience_csvs[vc], cofounders_volunteering_csvs[vc],\
      investment_managers_csvs[vc], investment_managers_education_csvs[vc],\
      investment_managers_experience_csvs[vc], investment_managers_volunteering_csvs[vc]\
      = csv_names_for_vc(vc)
      
      cofounders_education_jsons[vc], cofounders_experience_jsons[vc],\
      cofounders_volunteering_jsons[vc], investment_managers_education_jsons[vc],\
      investment_managers_experience_jsons[vc], investment_managers_volunteering_jsons[vc]\
      = json_names_for_vc(vc)

    network.generate.vc_company_network(portfolio_csvs, overwrite)
    network.generate.company_cofounder_network(cofounders_inv_manager_csvs, overwrite)
    network.generate.company_inv_manager_network(cofounders_inv_manager_csvs, overwrite)
    
    network.generate.cofounder_education_network(cofounders_education_jsons, overwrite)
    network.generate.cofounder_experience_network(cofounders_experience_jsons, overwrite)
    network.generate.cofounder_volunteering_network(cofounders_volunteering_jsons, overwrite)

    network.generate.inv_manager_education_network(investment_managers_education_jsons, overwrite)
    network.generate.inv_manager_experience_network(investment_managers_experience_jsons, overwrite)
    network.generate.inv_manager_volunteering_network(investment_managers_volunteering_jsons, overwrite)

    network.generate.cofounder_inv_manager_network(
      cofounders_inv_manager_csvs,
      cofounders_education_jsons,
      investment_managers_education_jsons,
      cofounders_experience_jsons,
      investment_managers_experience_jsons,
      cofounders_volunteering_jsons,
      investment_managers_volunteering_jsons,
      overwrite
    )

if __name__ == "__main__":
  configure_logging()
  load_dotenv()
  args = [arg for arg in sys.argv[1:] if arg != "--overwrite" and arg != "--collect" and arg != "--scrape" and arg != "--network"]
  overwrite_flag = "--overwrite" in sys.argv
  collect_flag = "--collect" in sys.argv
  scrape_flag = "--scrape" in sys.argv
  network_flag = "--network" in sys.argv
  if len(args) != 0:
    logger.error("Usage: uv run main.py [--overwrite] [--collect] [--scrape] [--network]")
    exit(os.EX_USAGE)

  main(overwrite = overwrite_flag, collect_flag = collect_flag, scrape_flag = scrape_flag, network_flag = network_flag)