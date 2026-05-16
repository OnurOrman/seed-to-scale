import asyncio
import os
import sys

from dotenv import load_dotenv

from collect import investment_managers, linkedin, vc_212
from helpers.logging import configure_logging, get_logger

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
      
      cofounders_csv, cofounders_education_csv, cofounders_experience_csv,\
        cofounders_volunteering_csv, employees_csv\
          = asyncio.run(linkedin.main(vc, vc_linkedin, overwrite = overwrite))
      
      investment_manager_json = investment_managers.get_investment_managers(
        investment_managers.collect_investment_managers(
          team_csv,
          employees_csv,
          portfolio_csv,
          overwrite = overwrite,
        )
      )

      investment_managers_csv, investment_managers_education_csv,\
        investment_managers_experience_csv, investment_managers_volunteering_csv\
          = asyncio.run(linkedin.vc_investment_managers(
            vc,
            investment_manager_json,
            overwrite = overwrite,
          ))
      
      logger.info("Collected the data for %s", vc)
  else:
    pass


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