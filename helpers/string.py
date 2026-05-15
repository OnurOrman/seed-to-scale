import re

from urllib.parse import urlparse

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
  final_names = []

  for initial_name in initial_names:
    for split_name in split_possible_names(initial_name):
      formatted = deturkify(split_name)
      if formatted not in final_names:
        final_names.append(formatted.replace(" ", separator, formatted.count(" ")))

  return final_names

def exclude_abbreviated_names(full_name: str) -> str:
  final_name = ""
  for word in full_name.split(" "):
    if not word.endswith("."):
      final_name += " " + word

  return final_name.strip()

def clean_link(link: str) -> str:
  return link[:link.find("?") - 1] if link.find("?") != -1 else link[:-1] if link[-1] == "/" else link