import re

from urllib.parse import urlparse

from helpers.constants import *

def company_name_from_parent_link(parent_link: str) -> str:
  path = urlparse(parent_link).path.strip("/")
  slug = path.split("/")[-1] if path else ""
  return slug.replace("-", " ").title() if slug else parent_link

def split_possible_names(raw_text: str) -> list[str]:
  text = raw_text.strip()
  if not text:
    return []

  # Split multi-name strings like "Alice, Bob", "Alice and Bob",
  # "Alice & Bob", "Alice / Bob", or names separated by newlines.
  parts = re.split(r"\s*(?:\n+|,|;|\band\b|&|/|\|)\s*", text, flags = re.IGNORECASE)
  cleaned = [p.strip() for p in parts if p and p.strip()]
  return cleaned or [text]

def split_links(raw_links: str) -> list[str]:
  if not isinstance(raw_links, str):
    return []

  links = raw_links.strip()
  if not links:
    return []
  
  parts = links.split("|")
  cleaned = [clean_link(p.strip()) for p in parts if p and p.strip()]
  return cleaned

def deturkify(string: str) -> str:
  return string.replace("Ç", "C", string.count("Ç"))\
    .replace("ç", "c", string.count("ç"))\
    .replace("Ğ", "G", string.count("Ğ"))\
    .replace("ğ", "g", string.count("ğ"))\
    .replace("ı", "i", string.count("ı"))\
    .replace("İ", "I", string.count("İ"))\
    .replace("Ö", "O", string.count("Ö"))\
    .replace("ö", "o", string.count("ö"))\
    .replace("Ş", "S", string.count("Ş"))\
    .replace("ş", "s", string.count("ş"))\
    .replace("Ü", "U", string.count("Ü"))\
    .replace("ü", "u", string.count("ü"))

def extract_unique_names(initial_names: list[str], separator: str = " ") -> list[str]:
  names = []

  for initial_name in initial_names:
    for split_name in split_possible_names(initial_name):
      formatted = deturkify(split_name)
      if formatted not in names:
        names.append(formatted.replace(" ", separator, formatted.count(" ")))
  # No sorting as the names and links may mismatch
  final_names = list(dict.fromkeys(names))
  return final_names

def extract_unique_links(initial_links: list[str]) -> list[str]:
  links = []

  for initial_link in initial_links:
    for split_link in split_links(initial_link):
      if split_link not in links:
        links.append(split_link)
  # No sorting as the names and links may mismatch
  final_links = list(dict.fromkeys(links))
  return final_links

def exclude_abbreviated_names(full_name: str) -> str:
  final_name = ""
  for word in full_name.split(" "):
    if not word.endswith("."):
      final_name += " " + word

  return final_name.strip()

def clean_link(link: str) -> str:
  return link[:link.find("/?")] if "/?" in link\
    else link[:link.find("?")] if "?" in link\
      else link[:-1] if link[-1] == "/"\
        else link

def csv_names_for_vc(vc: str):
  return (
    f"{vc}_{PORTFOLIO_CSV}",
    f"{vc}_{TEAM_CSV}",
    f"{vc}_{COFOUNDER_INVESTMENT_CSV}",
    f"{vc}_{COFOUNDER_MAIN_CSV}",
    f"{vc}_{COFOUNDER_EDU_CSV}",
    f"{vc}_{COFOUNDER_EXP_CSV}",
    f"{vc}_{COFOUNDER_VOL_CSV}",
    f"{vc}_{EMPLOYEE_MAIN_CSV}",
    f"{vc}_{EMPLOYEE_EDU_CSV}",
    f"{vc}_{EMPLOYEE_EXP_CSV}",
    f"{vc}_{EMPLOYEE_VOL_CSV}"
  )

def json_names_for_vc(vc: str):
  return (
    f"{vc}_{COFOUNDER_EDU_JSON}",
    f"{vc}_{COFOUNDER_EXP_JSON}",
    f"{vc}_{COFOUNDER_VOL_JSON}",
    f"{vc}_{EMPLOYEE_EDU_JSON}",
    f"{vc}_{EMPLOYEE_EXP_JSON}",
    f"{vc}_{EMPLOYEE_VOL_JSON}"
  )

def format_name(name: str) -> str:
  formatted_name = ""
  for word in name.split(" "):
    formatted_name += f" {word.capitalize()}"

  formatted_name = formatted_name.replace(".", "", formatted_name.count("."))

  return formatted_name.strip()

def is_name_in(name1: str, name2: str):
  if name1 == name2:
    return True
  
  words_name1 = name1.split(" ")

  for word in words_name1:
    if word not in name2:
      return False
    
  return True