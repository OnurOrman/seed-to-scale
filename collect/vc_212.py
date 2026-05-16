import csv
import json
import os
import pandas as pd
import sys

from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin

from helpers.constants import CSV_PATH
from helpers.linkedin import clean_linkedin_link
from helpers.logging import configure_logging, get_logger
from helpers.string import *
from helpers.webscrape import is_element_hidden, scrape_website

logger = get_logger(__name__)

def collect_portfolio_links(url: str = "https://212.vc/portfolio", overwrite: bool = False) -> str:
  csv_path = Path(CSV_PATH)
  csv_path.mkdir(parents = True, exist_ok = True)
  portfolio_csv = "212_portfolio_links.csv"
  portfolio_csv_path = csv_path / portfolio_csv

  if portfolio_csv_path.exists() and not overwrite:
    logger.info("CSV already exists: %s", str(portfolio_csv_path))
    return portfolio_csv

  result = scrape_website(url)

  soup = BeautifulSoup(result.html, "html.parser")

  # Match divs like: <div class='media-box  category_...'>
  link_target_divs = [
    div
    for div in soup.find_all("div", class_=True)
    if "media-box" in " ".join(div.get("class", []))\
      and "category_" in " ".join(div.get("class", []))
  ]

  links = []
  for link_div in link_target_divs:
    for a_tag in link_div.find_all("a", href=True):
      links.append(urljoin(url, a_tag["href"]))


  name_target_divs = [
    div
    for div in soup.find_all("div", class_=True)
    if "post_title-1" in " ".join(div.get("class", []))\
      and "mb_hide_if_empty mb_global_skin" in " ".join(div.get("class", []))
  ]

  names = []
  for name_div in name_target_divs:
    names.append(name_div.contents[0].strip())


  # Deduplicate while preserving order
  unique_links = list(dict.fromkeys(links))
  unique_names = list(dict.fromkeys(names))

  unique_portfolio = []

  for name, link in zip(unique_names, unique_links):
    unique_portfolio.append({"company_name": name, "company_vc_link": link})

  unique_portfolio.sort(key = lambda company: company["company_name"])

  portfolio_df = pd.DataFrame(unique_portfolio)
  
  portfolio_df.to_csv(portfolio_csv_path, index = False, encoding = "utf-8")

  return portfolio_csv

def scrape_portfolio_links(csv_with_links: str, overwrite: bool = False):
  csv_path = Path(CSV_PATH)
  csv_path.mkdir(parents = True, exist_ok = True)

  output_csv = "212_cofounders_with_investment_managers.csv"
  output_csv_path = csv_path / output_csv
  if output_csv_path.exists() and not overwrite:
    logger.info("CSV already exists: %s", str(output_csv_path))
    return output_csv

  path_to_links = Path(CSV_PATH) / csv_with_links

  portfolio_df = pd.read_csv(path_to_links)
  portfolio_links = portfolio_df["company_vc_link"]
  
  extracted_rows = []

  for company_link in portfolio_links:
    try:
      page_result = scrape_website(company_link)
      soup = BeautifulSoup(page_result.html, "html.parser")

      # LinkedIn buttons: <a class="elementor-button elementor-button-link elementor-size-sm" href="https://www.linkedin.com/in/...">
      linkedin_anchors = soup.select("a.elementor-button.elementor-button-link.elementor-size-sm[href]")
      linkedin_links = [
        clean_linkedin_link(a["href"].strip())
        for a in linkedin_anchors
        if "linkedin.com/in/" in a["href"].strip()
      ]

      # Co-founder names: <h2 class="elementor-heading-title elementor-size-default">Name, ...</h2>
      name_nodes = soup.select("h2.elementor-heading-title.elementor-size-default")
      founder_names = []
      for node in name_nodes:
        raw_name = node.get_text(strip = True)
        clean_name = raw_name.split(",")[0].strip()
        if clean_name:
          founder_names.append(clean_name)

      # Investment manager blocks:
      # <h3 ...>Investment Manager</h3> + <h4 ...>Name Surname</h4> in the same container
      investment_manager_names = []
      for container in soup.select("div[data-element_type='container']"):
        role_node = container.select_one("h3.elementor-heading-title")
        if role_node is None:
          continue
        role_text = role_node.get_text(" ", strip = True).lower()
        if "investment manager" not in role_text:
          continue

        for manager_node in container.select("h4.elementor-heading-title"):
          # Preserve explicit line breaks (including <br>) so multi-manager text can be split reliably.
          manager_text = manager_node.get_text("\n", strip = True)
          for manager_name in split_possible_names(manager_text):
            if manager_name:
              investment_manager_names.append(manager_name)

      # Deduplicate while preserving order.
      investment_manager_names = list(dict.fromkeys(investment_manager_names))

      # Pair co-founder names and LinkedIn links by order into one structured list.
      pair_len = max(len(founder_names), len(linkedin_links))
      cofounders = []
      for idx in range(pair_len):
        cofounders.append(
          {
            "name": founder_names[idx] if idx < len(founder_names) else "",
            "linkedin": linkedin_links[idx] if idx < len(linkedin_links) else "",
          }
        )

      company_name = company_name_from_parent_link(company_link)

      # 1. Find all potential LinkedIn company links in the HTML
      potential_links = []
      # Check social icons
      for a in soup.select("a.elementor-social-icon-linkedin[href]"):
        potential_links.append(a["href"].strip())
      # Check icon-box links
      for a in soup.select("div.elementor-icon-box-icon a[href]"):
        potential_links.append(a["href"].strip())
          
      company_linkedin = ""
      clean_name_slug = company_name.lower().replace(" ", "").replace("-", "")

      for raw_url in potential_links:
        if "linkedin.com/company/" in raw_url:
            parts = raw_url.split("/")
            try:
              idx = parts.index("company")
              slug = parts[idx + 1]
              clean_slug = slug.lower().replace("-", "").replace("_", "")
              
              # Compatibility check: one must be contained in the other
              if clean_slug in clean_name_slug or clean_name_slug in clean_slug:
                company_linkedin = f"https://www.linkedin.com/company/{slug}/"
                break # Found a compatible match, stop searching
            except (ValueError, IndexError):
              continue

      # 2. Fallback: Generate LinkedIn URL from the 212 link slug
      if not company_linkedin:
        # Example: https://212.vc/aepnus/ -> aepnus
        path = urlparse(company_link).path.strip("/")
        slug = path.split("/")[-1] if path else ""
        if slug:
          company_linkedin = f"https://www.linkedin.com/company/{slug}/"

      extracted_rows.append(
        {
          "company_name": company_name,
          "parent_link": company_link,
          "cofounders": cofounders,
          "investment_managers": investment_manager_names,
          "cofounder_count": len([c for c in cofounders if c.get("name")]),
          "investment_manager_count": len(investment_manager_names),
          "company_linkedin": company_linkedin
        }
      )

    except Exception as exc:
      extracted_rows.append(
        {
          "company_name": company_name_from_parent_link(company_link),
          "parent_link": company_link,
          "cofounders": [],
          "investment_managers": [],
          "cofounder_count": 0,
          "investment_manager_count": 0,
          "company_linkedin": "",
          "error": str(exc),
        }
      )
    
  fieldnames = [
    "company_name",
    "parent_link",
    "company_linkedin",
    "cofounder_count",
    "investment_manager_count",
    "cofounders_name",
    "cofounders_linkedin",
    "investment_managers",
    "cofounders_json",
    "investment_managers_json",
    "error",
  ]

  with open(output_csv_path, "w", newline = "", encoding = "utf-8") as out_file:
    writer = csv.DictWriter(out_file, fieldnames = fieldnames)
    writer.writeheader()

    for row in extracted_rows:
      cofounders = row.get("cofounders", [])
      investment_managers = row.get("investment_managers", [])
      cofounders_name = [c.get("name", "") for c in cofounders if c.get("name", "")]
      cofounders_linkedin = [c.get("linkedin", "") for c in cofounders if c.get("linkedin", "")]

      writer.writerow(
        {
          "company_name": row.get("company_name", ""),
          "parent_link": row.get("parent_link", ""),
          "company_linkedin": row.get("company_linkedin", ""),
          "cofounder_count": row.get("cofounder_count", len(cofounders_name)),
          "investment_manager_count": row.get("investment_manager_count", len(investment_managers)),
          "cofounders_name": " | ".join(cofounders_name),
          "cofounders_linkedin": " | ".join(cofounders_linkedin),
          "investment_managers": " | ".join(investment_managers),
          "cofounders_json": json.dumps(cofounders, ensure_ascii = False),
          "investment_managers_json": json.dumps(investment_managers, ensure_ascii = False),
          "error": row.get("error", ""),
        }
      )

  logger.info(
    "Saved %s company rows to %s",
    len(extracted_rows),
    str(output_csv_path),
  )
  return output_csv

def collect_team_links(url: str = "https://212.vc/team", overwrite: bool = False) -> str:
  output_csv = "212_employees_team.csv"
  output_csv_path = Path(CSV_PATH) / output_csv

  if output_csv_path.exists() and not overwrite:
    logger.info("CSV already exists: %s", str(output_csv_path))
    return output_csv

  result = scrape_website(url)

  soup = BeautifulSoup(result.html, "html.parser")

  # Some former employees are hidden
  all_divs = soup.find_all("div", class_ = True)
  hidden_divs = [
    div for div in all_divs
    if all(cls in div.get("class", [])\
      for cls in ["elementor-hidden-desktop", "elementor-hidden-tablet", "elementor-hidden-mobile"])
  ]

  links = []
  names = []

  # Scrape LinkedIn links from items that are NOT hidden
  target_lis = [
    li
    for li in soup.find_all("li", class_ = True)
    if "elementor-icon-list-item elementor-inline-item" in " ".join(li.get("class", []))
  ]
  for li in target_lis:
    if is_element_hidden(li, hidden_divs):
      continue

    for a_tag in li.find_all("a", href = True):
      if "linkedin.com" in a_tag["href"] and a_tag["href"] not in links:
        links.append(clean_linkedin_link(a_tag["href"]))
    
  target_spans = [
    span
    for span in soup.find_all("span", class_ = True)
    if "elementor-cta__title elementor-cta__content-item elementor-content-item" in " ".join(span.get("class", []))
  ]

  for span in target_spans:
    if is_element_hidden(span, hidden_divs):
      continue

    formatted_name = deturkify(span.contents[0].strip())

    if formatted_name not in names:
      finalized_name = exclude_abbreviated_names(formatted_name)

      names.append(finalized_name)
  
  # Deduplicate while preserving order
  unique_employee_links = list(dict.fromkeys(links))
  unique_employee_names = list(dict.fromkeys(names))

  fieldnames = [
    "employee_name",
    "employee_linkedin"
  ]

  with open(output_csv_path, "w", newline = "", encoding = "utf-8") as out_file:
    writer = csv.DictWriter(out_file, fieldnames = fieldnames)
    writer.writeheader()

    for name, linkedin_link in zip(unique_employee_names, unique_employee_links):
      writer.writerow({
        "employee_name": name,
        "employee_linkedin": linkedin_link
      })

  logger.info(
    "Saved %s company rows to %s",
    len(unique_employee_links),
    str(output_csv_path),
  )
  return output_csv

def main(overwrite: bool = False):
  configure_logging()
  portfolio_links = collect_portfolio_links(overwrite = overwrite)
  portfolio_csv = scrape_portfolio_links(portfolio_links, overwrite = overwrite)
  team_csv = collect_team_links(overwrite = overwrite)
  return portfolio_csv, team_csv

if __name__ == "__main__":
  overwrite_flag = "--overwrite" in sys.argv
  if len([arg for arg in sys.argv[1:] if arg != "--overwrite"]) != 0:
    logger.error("Usage: uv run -m collect.vc_212 [--overwrite]")
    exit(os.EX_USAGE)
  
  main(overwrite = overwrite_flag)