import asyncio
import os
import sys

from collect import investment_managers, linkedin, vc_212
from helpers.logging import configure_logging, get_logger

logger = get_logger(__name__)

def main(vc: str, vc_linkedin: str):
  logger.info("Starting seed-to-scale run.")
  portfolio_csv = ""
  team_csv = ""

  if vc == "212":
    portfolio_csv, team_csv = vc_212.main()
  
  cofounders_csv, cofounders_education_csv, cofounders_experience_csv,\
    cofounders_volunteering_csv, employees_csv\
      = asyncio.run(linkedin.main(vc, vc_linkedin))
  
  investment_manager_json = investment_managers.get_investment_managers(
    investment_managers.collect_investment_managers(
      team_csv, employees_csv, portfolio_csv
    )
  )

  investment_managers_csv, investment_managers_education_csv, investment_managers_experience_csv,\
    investment_managers_volunteering_csv\
      = asyncio.run(linkedin.vc_investment_managers(vc, investment_manager_json))
  
  logger.info("Collected the data for %s", vc)

if __name__ == "__main__":
  configure_logging()
  if len(sys.argv) != 3:
    logger.error("Usage: uv run main.py <vc-name> <vc-linkedin-url>")
    exit(os.EX_USAGE)

  main(sys.argv[1], sys.argv[2])