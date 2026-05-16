import asyncio
import os
import sys

from dotenv import load_dotenv

from collect import investment_managers, linkedin, vc_212
from helpers.logging import configure_logging, get_logger
from helpers.string import csv_names_for_vc

logger = get_logger(__name__)

def main(overwrite: bool = False, collect: bool = False, network: bool = False):
  logger.info("Starting seed-to-scale run.")
  portfolio_csv = ""
  team_csv = ""

  vcs = os.getenv("VC").split(",")
  vc_linkedins = os.getenv("VC_LINKEDIN").split(",")

  if collect:
    for vc, vc_linkedin in zip(vcs, vc_linkedins):
      if vc == "212":
        portfolio_csv, team_csv = vc_212.main(overwrite = overwrite)
      
      employees_csv = asyncio.run(linkedin.main(
        vc, vc_linkedin, overwrite = overwrite
      ))
      
      investment_manager_json = investment_managers.get_investment_managers(
        investment_managers.collect_investment_managers(
          team_csv,
          employees_csv,
          portfolio_csv,
          overwrite = overwrite,
        )
      )

      asyncio.run(linkedin.vc_investment_managers(
        vc,
        investment_manager_json,
        overwrite = overwrite,
      ))
      
      logger.info("Collected the data for %s", vc)

  if network:
    portfolio_csvs = dict()
    team_csvs = dict()
    cofounders_csvs = dict(); cofounders_education_csvs = dict()
    cofounders_experience_csvs = dict(); cofounders_volunteering_csvs = dict()

    investment_managers_csvs = dict(); investment_managers_education_csvs = dict()
    investment_managers_experience_csvs = dict(); investment_managers_volunteering_csvs = dict()

    for vc in vcs:
      portfolio_csvs[vc], team_csvs[vc],\
      cofounders_csvs[vc], cofounders_education_csvs[vc],\
      cofounders_experience_csvs[vc], cofounders_volunteering_csvs[vc],\
      investment_managers_csvs[vc], investment_managers_education_csvs[vc],\
      investment_managers_experience_csvs[vc], investment_managers_volunteering_csvs[vc]\
      = csv_names_for_vc(vc)

    


if __name__ == "__main__":
  configure_logging()
  load_dotenv()
  args = [arg for arg in sys.argv[1:] if arg != "--overwrite" and arg != "--collect" and arg != "--network"]
  overwrite_flag = "--overwrite" in sys.argv
  collect_flag = "--collect" in sys.argv
  network_flag = "--network" in sys.argv
  if len(args) != 0:
    logger.error("Usage: uv run main.py [--overwrite] [--collect] [--network]")
    exit(os.EX_USAGE)

  main(overwrite = overwrite_flag, collect = collect_flag, network = network_flag)