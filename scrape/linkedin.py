import json
import os
import pandas as pd
import sys

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pathlib import Path

from collect.investment_managers import get_investment_managers
from helpers.constants import *
from helpers.logging import *
from helpers.string import *

logger = get_logger(__name__)

def scrape_linkedin_pages(vc: str, names_links: dict[str, str], category: str, linkedin_page: str = "", overwrite: bool = False):
  # Education: div class: _9e198690 _81f0ce2b f82dffd8 _56dcffcd _11b7743d _2b989295 _3d7860a2
  # Experience: div class: _905c4fe2 _81f0ce2b _4904c7ef _56dcffcd _541acca0 _86dbe298 _3d7860a2; entity-collection-item componentkey of div
  # Volunteering: div class: _905c4fe2 dd265f4a _81f0ce2b _4904c7ef _56dcffcd _541acca0 _86dbe298 _3d7860a2

  out_json_dict = dict()
  out_json_file = f"{vc}_{category}_{linkedin_page if linkedin_page != "" else "main"}{JSON_EXT}"
  out_json_path = Path(JSON_PATH) / out_json_file

  if out_json_path.exists() and not overwrite:
    return

  target = f"{vc}_{category}_linkedin_{linkedin_page if linkedin_page != "" else "main"}"

  target_csv = f"{target}{CSV_EXT}"
  target_csv_path = Path(CSV_PATH) / target_csv

  target_html_dir = Path(HTML_PATH) / target

  target_df = pd.read_csv(target_csv_path)

  for name, links in names_links.items():
    for link in links:
      target_link = f"{link}{DETAILS_LINKEDIN}/{linkedin_page}"
      target_html_files = target_df[target_df["url"] == target_link]["file_path"].tolist()

      if len(target_html_files) == 1:
        target_html_file = target_html_files[0]
      
        target_html_path = target_html_dir / target_html_file

        with open(target_html_path, "r", encoding = "utf-8") as f:
          html_content = f.read()

          soup = BeautifulSoup(html_content, "html.parser")
          target_ps = []

          if linkedin_page == EDUCATION:
            target_ps = soup.find_all("p", class_ = True)
            education_info = []
            current_education_info = dict()

            # School - p class: d8d5bbbc _2f6a5622 _2dffdc6d _6718f443 _8701cd9e cfeff318 _24f71c1d e2a4ad5d e4602472 _444aef97 _74fd65b3
            # Major - p class: d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d e2a4ad5d e4602472 _07666e83
            # Additional - p class: d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d _98cb9b8f e4602472 _07666e83

            for target_p in target_ps:
              if "d8d5bbbc _2f6a5622 _2dffdc6d _6718f443 _8701cd9e cfeff318 _24f71c1d e2a4ad5d e4602472 _444aef97 _74fd65b3" in " ".join(target_p.get("class", [])):
                current_education_info = dict()
                current_education_info["school"] = target_p.contents[0].strip()

              elif "d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d e2a4ad5d e4602472 _07666e83" in " ".join(target_p.get("class", [])):
                current_education_info["major"] = target_p.contents[0].strip()
                education_info.append(current_education_info)

              elif "d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d _98cb9b8f e4602472 _07666e83" in " ".join(target_p.get("class", [])):
                if current_education_info in education_info:
                  education_info.remove(current_education_info)
                
                current_education_info["additional"] = target_p.contents[0].strip()
                education_info.append(current_education_info)
              
            out_json_dict[name] = education_info
          elif linkedin_page == EXPERIENCE:
            target_ps = soup.find_all("p", class_ = True)
            experience_info = []
            current_experience_info = dict()

            # Position - p class: d8d5bbbc _2f6a5622 _2dffdc6d _6718f443 _8701cd9e cfeff318 _24f71c1d e2a4ad5d e4602472 _444aef97 _74fd65b3
            # Company - p class: d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d e2a4ad5d e4602472 _07666e83
            # Additional - p class: d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d e2a4ad5d e4602472 _07666e83

            for target_p in target_ps:
              if "d8d5bbbc _2f6a5622 _2dffdc6d _6718f443 _8701cd9e cfeff318 _24f71c1d e2a4ad5d e4602472 _444aef97 _74fd65b3" in " ".join(target_p.get("class", [])):
                current_experience_info = dict()
                current_experience_info["position"] = target_p.contents[0].strip()

              elif "d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d e2a4ad5d e4602472 _07666e83" in " ".join(target_p.get("class", [])):
                current_company = target_p.contents[0].strip()
                current_company = current_company[:current_company.find(" · ")]
                current_experience_info["company"] = current_company
                experience_info.append(current_experience_info)

              elif "d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d _98cb9b8f e4602472 _07666e83" in " ".join(target_p.get("class", [])):
                if current_experience_info in experience_info:
                  experience_info.remove(current_experience_info)

                current_experience_info["additional"] = target_p.contents[0].strip()
                experience_info.append(current_experience_info)
              
            out_json_dict[name] = experience_info
          elif linkedin_page == VOLUNTEERING:
            target_ps = soup.find_all("p", class_ = True)
            volunteering_info = []
            current_volunteering_info = dict()

            # Position - p class: d8d5bbbc _2f6a5622 _2dffdc6d _6718f443 _8701cd9e cfeff318 _24f71c1d e2a4ad5d e4602472 _444aef97 _74fd65b3
            # Organization - p class: d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d e2a4ad5d e4602472 _07666e83
            # Additional - p class: d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d e2a4ad5d e4602472 _07666e83

            for target_p in target_ps:
              if "d8d5bbbc _2f6a5622 _2dffdc6d _6718f443 _8701cd9e cfeff318 _24f71c1d e2a4ad5d e4602472 _444aef97 _74fd65b3" in " ".join(target_p.get("class", [])):
                current_volunteering_info = dict()
                current_volunteering_info["position"] = target_p.contents[0].strip()

              elif "d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d e2a4ad5d e4602472 _07666e83" in " ".join(target_p.get("class", [])):
                current_volunteering_info["organization"] = target_p.contents[0].strip()
                volunteering_info.append(current_volunteering_info)

              elif "d8d5bbbc bab73015 _2dffdc6d _6718f443 e1321d56 a5c40a37 _24f71c1d _98cb9b8f e4602472 _07666e83" in " ".join(target_p.get("class", [])):
                if current_volunteering_info in volunteering_info:
                  volunteering_info.remove(current_volunteering_info)
                
                current_volunteering_info["additional"] = target_p.contents[0].strip()
                volunteering_info.append(current_volunteering_info)

            out_json_dict[name] = volunteering_info

  with open(out_json_path, "w", encoding = "utf-8") as f:
    json.dump(out_json_dict, f, indent = 2, ensure_ascii = False)   

def main(overwrite: bool = False):
  configure_logging()

  vcs = os.getenv("VC").split(",")

  for vc in vcs:
    cofounders_inv_managers_path = Path(CSV_PATH) / f"{vc}_{COFOUNDER_INVESTMENT_CSV}"
    cofounders_inv_managers_df = pd.read_csv(cofounders_inv_managers_path)
    initial_cofounder_names = [cofounders_inv_managers_df.iloc[i]["cofounders_name"]\
                   for i in range(len(cofounders_inv_managers_df))\
                  if cofounders_inv_managers_df.iloc[i]["cofounder_count"] > 0 and pd.notna(cofounders_inv_managers_df.iloc[i]["cofounders_linkedin"])]
    vc_cofounder_names = extract_unique_names(initial_cofounder_names)
    initial_cofounder_links = [cofounders_inv_managers_df.iloc[i]["cofounders_linkedin"]\
                   for i in range(len(cofounders_inv_managers_df))\
                  if cofounders_inv_managers_df.iloc[i]["cofounder_count"] > 0 and pd.notna(cofounders_inv_managers_df.iloc[i]["cofounders_linkedin"])]
    cofounder_links = extract_unique_links(initial_cofounder_links)

    linkedin_vc_cofounders_csv = f"{vc}_{COFOUNDER_MAIN_CSV}"
    linkedin_vc_cofounders_path = Path(CSV_PATH) / linkedin_vc_cofounders_csv
    linkedin_vc_cofounders_df = pd.read_csv(linkedin_vc_cofounders_path)
    linkedin_vc_cofounders_names = [format_name(deturkify(linkedin_vc_cofounders_df.iloc[i]["title"][:linkedin_vc_cofounders_df.iloc[i]["title"].find(",")]))\
                                    if "," in linkedin_vc_cofounders_df.iloc[i]["title"]\
                                      else format_name(deturkify(linkedin_vc_cofounders_df.iloc[i]["title"][:linkedin_vc_cofounders_df.iloc[i]["title"].find(" | ")]))\
                                        for i in range(len(linkedin_vc_cofounders_df))]
    
    cofounder_names = []
    for vc_cofounder_name in vc_cofounder_names:
      for linkedin_vc_cofounder_name in linkedin_vc_cofounders_names:
        if (vc_cofounder_name not in cofounder_names) and (linkedin_vc_cofounder_name not in cofounder_names):
          if is_name_in(vc_cofounder_name, linkedin_vc_cofounder_name):
            cofounder_names.append(linkedin_vc_cofounder_name)
          elif is_name_in(linkedin_vc_cofounder_name, vc_cofounder_name):
            cofounder_names.append(vc_cofounder_name)

    cofounder_info = {cofounder_name: [cofounder_link] for cofounder_name, cofounder_link in zip(cofounder_names, cofounder_links)}
    scrape_linkedin_pages(vc, cofounder_info, COFOUNDER, EDUCATION, overwrite)
    scrape_linkedin_pages(vc, cofounder_info, COFOUNDER, EXPERIENCE, overwrite)
    scrape_linkedin_pages(vc, cofounder_info, COFOUNDER, VOLUNTEERING, overwrite)

    inv_managers_dict = get_investment_managers(f"{vc}_{INV_MANAGERS_JSON}")
    scrape_linkedin_pages(vc, inv_managers_dict, EMPLOYEE, EDUCATION, overwrite)
    scrape_linkedin_pages(vc, inv_managers_dict, EMPLOYEE, EXPERIENCE, overwrite)
    scrape_linkedin_pages(vc, inv_managers_dict, EMPLOYEE, VOLUNTEERING, overwrite)



if __name__ == "__main__":
  load_dotenv()
  args = [arg for arg in sys.argv[1:] if arg != "--overwrite"]
  overwrite_flag = "--overwrite" in sys.argv

  if len(args) != 0:
    logger.error("Usage: uv run -m scrape.linkedin [--overwrite]")
    exit(os.EX_USAGE)

  main(overwrite = overwrite_flag)