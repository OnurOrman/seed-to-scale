import asyncio
import os
import sys

from collect import investment_managers, linkedin, vc_212

def main(vc: str, vc_linkedin: str):
  print("Hello from seed-to-scale!")
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

if __name__ == "__main__":
  if len(sys.argv) != 3:
    print("Usage: uv run python main.py <vc-name> <vc-linkedin-url>")
    exit(os.EX_USAGE)

  # 212 -> 212, https://www.linkedin.com/company/212vc
  main(sys.argv[1], sys.argv[2])
