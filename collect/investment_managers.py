import json
import pandas as pd

from pathlib import Path

from helpers.constants import *
from helpers.string import *

def __retrieve_investment_managers(filename: str):
  file_path = Path(CSV_PATH) / filename
  df = pd.read_csv(file_path)

  initial_investment_manager_names = df["investment_managers"].dropna().unique().tolist()

  return sorted(extract_unique_names(initial_investment_manager_names))

def collect_investment_managers(team_file: str, linkedin_file: str, portfolio_file: str):
  team_path = Path(CSV_PATH) / team_file
  linkedin_path = Path(CSV_PATH) / linkedin_file
  
  vc = portfolio_file.split("_")[0]
  json_file = f"{vc}_investment_managers.json"
  json_path = Path(JSON_PATH) / json_file

  team_df = pd.read_csv(team_path, index_col = "employee_name")
  linkedin_df = pd.read_csv(linkedin_path, index_col = "employee_name")

  links_for_investment_managers = dict()
  investment_managers = __retrieve_investment_managers(portfolio_file)

  for investment_manager in investment_managers:
    try:
      links_for_investment_managers[investment_manager] = [team_df.loc[investment_manager]["employee_linkedin"]]
    except:
      links_for_investment_managers[investment_manager] = []

    try:
      if linkedin_df.loc[investment_manager]["employee_linkedin"] not in links_for_investment_managers[investment_manager]:
        links_for_investment_managers[investment_manager].append(linkedin_df.loc[investment_manager]["employee_linkedin"])
    except:
      continue

  with open(json_path, "w") as f:
    json.dump(links_for_investment_managers, f, indent = 2)

  return json_file

def get_investment_managers(json_file: str):
  json_path = Path(JSON_PATH) / json_file

  with open(json_path, "r") as f:
    investment_manager_data = json.load(f)
    return investment_manager_data