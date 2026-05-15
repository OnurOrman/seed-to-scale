import asyncio
import csv
import os
import pandas as pd
import sys

from bs4 import BeautifulSoup
from pathlib import Path

from helpers.constants import CSV_PATH, HTML_PATH, STATE_PATH
from helpers.linkedin import *
from helpers.logging import configure_logging, get_logger
from helpers.string import deturkify, extract_unique_names

logger = get_logger(__name__)

async def scrape_linkedin_people_from_csv(data_with_links: str, category: str, linkedin_page: str = ""):
  csv_path = Path(CSV_PATH) / data_with_links
  state_path = Path(STATE_PATH) / "li_playwright_state.json"
  df = pd.read_csv(csv_path)

  linkedin_links = sorted(
    {
      part.strip() + linkedin_page
      for link in df.get(f"{category}_linkedin", [])
      if pd.notna(link)
      for part in str(link).split("|")
      if "linkedin.com/in/" in part
    }
  )

  logger.info("Total number of LinkedIn links to scrape: %s", len(linkedin_links))

  out_dir = Path(HTML_PATH) / f"linkedin_{category}_{linkedin_page if linkedin_page != "" else "main"}"
  out_dir.mkdir(parents = True, exist_ok = True)

  if not state_path.exists():
    logger.warning("Login state not found. Triggering login flow...")
    await save_logged_in_state(
      login_url="https://www.linkedin.com/login",
      timeout_ms=180000,
    )

  rows = []

  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=False)
    # Load the saved state
    context = await browser.new_context(storage_state=state_path)
    page = await context.new_page()

    url: str
    for i, url in enumerate(linkedin_links, start=1):
      logger.info("[%s/%s] Scraping: %s", i, len(linkedin_links), url)
      
      html_file = f"linkedin_{i:04d}.html"
      html_path = out_dir / html_file
      if html_path.exists() and html_path.stat().st_size > 100:
        logger.info("Already scraped.")
        continue
          
      try:
        # "commit" returns as soon as network response is received, avoiding timeouts 
        # from endless background trackers holding up the "networkidle" state.
        await page.goto(url, wait_until="commit", timeout=60000)
        
        # Explicit physical sleep allows the React application to fully render 
        # all delayed or lazy-loaded components into the DOM
        await page.wait_for_timeout(15000)
        
        html = await page.content()
        
        # Recover if blocked
        if looks_like_linkedin_auth_wall(html):
          logger.warning("Auth wall or challenge detected.")
          logger.warning("In the opened browser, solve challenge or login manually.")
          input("  Press Enter here to retry capture...")
          
          await page.reload(wait_until="commit", timeout=60000)
          await page.wait_for_timeout(15000)
          
          html = await page.content()
          await context.storage_state(path=state_path)
            
        title = await page.title()
        
        # Save HTML
        html_path.write_text(html, encoding="utf-8")
        
        rows.append({
          "url": url,
          "status": "ok",
          "title": title,
          "file_path": html_file,
          "error": ""
        })
        logger.info("Saved %s - Title: %s...", html_path.name, title[:40])
          
      except Exception as exc:
        error_msg = str(exc)
        logger.error("Error: %s", error_msg)
        
        rows.append({
          "url": url,
          "status": "error",
          "title": "",
          "file_path": "",
          "error": error_msg
        })
          
      # Rest 10 seconds between requests to avoid IP limits
      await page.wait_for_timeout(10000)
        
    await browser.close()
  
  result_csv = ""
  if rows:
    result_df = pd.DataFrame(rows)
    result_csv = f"{data_with_links.split("_")[0]}_{category}_linkedin_{linkedin_page if linkedin_page != "" else "main"}.csv"
    result_csv_path = Path(CSV_PATH) / result_csv
    
    if result_csv_path.exists():
      existing_df = pd.read_csv(result_csv)
      combined_df = pd.concat([existing_df, result_df]).drop_duplicates(subset=["url"], keep="last")
      combined_df.to_csv(result_csv, index=False, encoding="utf-8")
    else:
      result_df.to_csv(result_csv, index=False, encoding="utf-8")
        
    logger.info("Saved logging results to %s", CSV_PATH + "/" + result_csv)

  if not result_csv:
    logger.warning("No rows collected; skipping CSV output.")

  logger.info("Scraping complete.")

  return result_csv

async def scrape_linkedin_people_from_dict(vc: str, data: dict, category: str, linkedin_page: str = ""):
  state_path = Path(STATE_PATH) / "li_playwright_state.json"
  out_dir = Path(HTML_PATH) / f"linkedin_{category}_{linkedin_page if linkedin_page != "" else "main"}"
  out_dir.mkdir(parents = True, exist_ok = True)

  if not state_path.exists():
    logger.warning("Login state not found. Triggering login flow...")
    await save_logged_in_state(
      login_url="https://www.linkedin.com/login",
      timeout_ms=180000,
    )

  rows = []

  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=False)
    # Load the saved state
    context = await browser.new_context(storage_state=state_path)
    page = await context.new_page()

    for i, _ in enumerate(data, start=1):
      _, urls = list(data.keys())[i], list(data.values())[i]
      html_file = f"linkedin_{i:04d}.html"
      html_path = out_dir / html_file
      if html_path.exists() and html_path.stat().st_size > 100:
        logger.info("Already scraped.")
        continue
        
      for url in urls:
        try:
          # "commit" returns as soon as network response is received, avoiding timeouts 
          # from endless background trackers holding up the "networkidle" state.
          await page.goto(url, wait_until="commit", timeout=60000)
          
          # Explicit physical sleep allows the React application to fully render 
          # all delayed or lazy-loaded components into the DOM
          await page.wait_for_timeout(15000)
          
          html = await page.content()
          current_url = page.url

          # Check for 404 redirect
          if "linkedin.com/404" in current_url:
            logger.warning("Profile not found (404/redirect) at %s, trying next...", url)
            continue
          
          # Recover if blocked
          if looks_like_linkedin_auth_wall(html):
            logger.warning("Auth wall or challenge detected.")
            logger.warning("In the opened browser, solve challenge or login manually.")
            input("  Press Enter here to retry capture...")
            
            await page.reload(wait_until="commit", timeout=60000)
            await page.wait_for_timeout(15000)
            
            html = await page.content()
            await context.storage_state(path=state_path)
              
          title = await page.title()
          
          # Save HTML
          html_path.write_text(html, encoding="utf-8")
          
          rows.append({
            "url": url,
            "status": "ok",
            "title": title,
            "file_path": html_file,
            "error": ""
          })
          logger.info("Saved %s - Title: %s...", html_path.name, title[:40])
            
        except Exception as exc:
          error_msg = str(exc)
          logger.error("Error: %s", error_msg)
          
          rows.append({
            "url": url,
            "status": "error",
            "title": "",
            "file_path": "",
            "error": error_msg
          })
            
        # Rest 10 seconds between requests to avoid IP limits
        await page.wait_for_timeout(10000)
        
    await browser.close()
  
  result_csv = ""
  if rows:
    result_df = pd.DataFrame(rows)
    result_csv = f"{vc}_{category}_linkedin_{linkedin_page if linkedin_page != "" else "main"}.csv"
    result_csv_path = Path(CSV_PATH) / result_csv
    
    if result_csv_path.exists():
      existing_df = pd.read_csv(result_csv)
      combined_df = pd.concat([existing_df, result_df]).drop_duplicates(subset=["url"], keep="last")
      combined_df.to_csv(result_csv, index=False, encoding="utf-8")
    else:
      result_df.to_csv(result_csv, index=False, encoding="utf-8")
        
    logger.info("Saved logging results to %s", CSV_PATH + "/" + result_csv)

  if not result_csv:
    logger.warning("No rows collected; skipping CSV output.")

  logger.info("Scraping complete.")

  return result_csv

async def scrape_employee_lookup(data_with_links: str, vc_base_linkedin_url: str):
  csv_path = Path(CSV_PATH) / data_with_links
  state_path = Path(STATE_PATH) / "li_playwright_state.json"
  df = pd.read_csv(csv_path)

  initial_investment_manager_names = df["investment_managers"].dropna().unique().tolist()

  investment_manager_names = extract_unique_names(initial_investment_manager_names, "%20")

  out_dir = Path(HTML_PATH) / f"{data_with_links.split("_")[0]}_employees_linkedin_lookup"
  out_dir.mkdir(parents = True, exist_ok = True)

  if not state_path.exists():
    logger.warning("Login state not found. Triggering login flow...")
    await save_logged_in_state(
      login_url="https://www.linkedin.com/login",
      timeout_ms=180000,
    )

  rows = []

  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=False)
    # Load the saved state
    context = await browser.new_context(storage_state=state_path)
    page = await context.new_page()

    for i, name in enumerate(investment_manager_names, start=1):
      vc_employee_url = f"{vc_base_linkedin_url}/people/?keywords={name}&viewAsMember=true"
      logger.info("[%s/%s] Scraping: %s", i, len(investment_manager_names), vc_employee_url)
      
      html_file = out_dir / f"vc_employee_linkedin_{i:04d}.html"
      if html_file.exists() and html_file.stat().st_size > 100:
        logger.info("Already scraped.")
        continue
          
      try:
        # "commit" returns as soon as network response is received, avoiding timeouts 
        # from endless background trackers holding up the "networkidle" state.
        await page.goto(vc_employee_url, wait_until="commit", timeout=60000)
        
        # Explicit physical sleep allows the React application to fully render 
        # all delayed or lazy-loaded components into the DOM
        await page.wait_for_timeout(15000)
        
        html = await page.content()
        
        # Recover if blocked
        if looks_like_linkedin_auth_wall(html):
          logger.warning("Auth wall or challenge detected.")
          logger.warning("In the opened browser, solve challenge or login manually.")
          input("  Press Enter here to retry capture...")
          
          await page.reload(wait_until="commit", timeout=60000)
          await page.wait_for_timeout(15000)
          
          html = await page.content()
          await context.storage_state(path=state_path)
            
        title = await page.title()
        
        # Save HTML
        html_file.write_text(html, encoding="utf-8")
        
        rows.append({
          "url": vc_employee_url,
          "status": "ok",
          "title": title,
          "file_path": str(html_file),
          "error": ""
        })
        logger.info("Saved %s - Title: %s...", html_file.name, title[:40])
          
      except Exception as exc:
        error_msg = str(exc)
        logger.error("Error: %s", error_msg)
        
        rows.append({
          "url": vc_employee_url,
          "status": "error",
          "title": "",
          "file_path": "",
          "error": error_msg
        })
          
      # Rest 10 seconds between requests to avoid IP limits
      await page.wait_for_timeout(10000)
        
    await browser.close()
  
  if rows:
    result_df = pd.DataFrame(rows)
    result_csv = f"{data_with_links.split("_")[0]}_employee_lookup_linkedin.csv"
    result_csv_path = Path(CSV_PATH) / result_csv
    
    if result_csv_path.exists():
      existing_df = pd.read_csv(result_csv_path)
      combined_df = pd.concat([existing_df, result_df]).drop_duplicates(subset=["url"], keep="last")
      combined_df.to_csv(result_csv_path, index=False, encoding="utf-8")
    else:
      result_df.to_csv(result_csv_path, index=False, encoding="utf-8")
        
    logger.info("Saved logging results to %s", CSV_PATH + "/" + result_csv)

  logger.info("Scraping complete.")

  return f"{data_with_links.split("_")[0]}_employees_linkedin_lookup"

async def collect_employee_lookup(html_dir: str):
  vc = html_dir.split("_")[0]
  directory = Path(HTML_PATH) / html_dir
  employee_linkedin_links = []
  employee_linkedin_names = []

  for html_file in sorted(directory.glob("*.html")):
    with open(html_file, "r", encoding = "utf-8") as f:
      html_content = f.read()

      logger.info("Processing %s...", html_file.name)

      soup = BeautifulSoup(html_content, "html.parser")
      try:
        link_target_div = soup.find("div", attrs={"id": "ember204"})
        name_target_div = soup.find("div", attrs={"id": "ember206"})

        for a_tag in link_target_div.find_all("a", href=True):
          if a_tag["href"] not in employee_linkedin_links:
            employee_linkedin_links.append(clean_linkedin_link(a_tag["href"]))
        
        formatted_name = deturkify(name_target_div.contents[0].strip())
        if formatted_name not in employee_linkedin_names:
          employee_linkedin_names.append(formatted_name)

      except Exception as e:
        logger.warning("Parse error: %s", e)
        continue

  unique_employee_linkedin_links = list(dict.fromkeys(employee_linkedin_links))
  unique_employee_linkedin_names = list(dict.fromkeys(employee_linkedin_names))

  output_csv = f"{vc}_employees_linkedin.csv"
  output_csv_path = Path(CSV_PATH) / output_csv
  fieldnames = [
    "employee_name",
    "employee_linkedin"
  ]

  with open(output_csv_path, "w", newline="", encoding="utf-8") as out_file:
    writer = csv.DictWriter(out_file, fieldnames=fieldnames)
    writer.writeheader()

    for name, linkedin_link in zip(unique_employee_linkedin_names, unique_employee_linkedin_links):
      writer.writerow({
        "employee_name": name,
        "employee_linkedin": linkedin_link
      })

  logger.info(
    "Saved %s company rows to %s",
    len(unique_employee_linkedin_links),
    CSV_PATH + "/" + output_csv,
  )
  return output_csv

async def cofounders(vc: str):
  cofounders_csv = await scrape_linkedin_people_from_csv(f"{vc}_cofounders_with_investment_managers.csv", "cofounders")
  cofounders_education_csv = await scrape_linkedin_people_from_csv(f"{vc}_cofounders_with_investment_managers.csv", "cofounders", "/education")
  cofounders_experience_csv = await scrape_linkedin_people_from_csv(f"{vc}_cofounders_with_investment_managers.csv", "cofounders", "/experience")
  cofounders_volunteering_csv = await scrape_linkedin_people_from_csv(f"{vc}_cofounders_with_investment_managers.csv", "cofounders", "/volunteering-experiences")
  return cofounders_csv, cofounders_education_csv, cofounders_experience_csv, cofounders_volunteering_csv

async def vc_employees(vc: str, vc_linkedin: str):
  lookup_dir = await scrape_employee_lookup(f"{vc}_cofounders_with_investment_managers.csv", vc_linkedin)
  employee_csv = await collect_employee_lookup(lookup_dir)
  return employee_csv

async def vc_investment_managers(vc: str, data: dict):
  configure_logging()
  investment_managers_csv = await scrape_linkedin_people_from_dict(vc, data, "employee")
  investment_managers_education_csv = scrape_linkedin_people_from_dict(vc, data, "employee", "/education")
  investment_managers_experience_csv = await scrape_linkedin_people_from_dict(vc, data, "employee", "/experience")
  investment_managers_volunteering_csv = scrape_linkedin_people_from_dict(vc, data, "employee", "/volunteering-experiences")
  return investment_managers_csv, investment_managers_education_csv, investment_managers_experience_csv, investment_managers_volunteering_csv

async def main(vc: str, vc_linkedin: str):
  configure_logging()
  cofounders_csv, cofounders_education_csv, cofounders_experience_csv, cofounders_volunteering_csv = await cofounders(vc)
  employees_csv = await vc_employees(vc, vc_linkedin)
  return cofounders_csv, cofounders_education_csv, cofounders_experience_csv, cofounders_volunteering_csv, employees_csv

if __name__ == "__main__":
  if len(sys.argv) != 3:
    logger.error("Usage: uv run -m collect.linkedin <vc-name> <vc-linkedin-url>")
    exit(os.EX_USAGE)

  asyncio.run(main(sys.argv[1], sys.argv[2]))