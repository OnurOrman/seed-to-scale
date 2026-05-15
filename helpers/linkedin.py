from pathlib import Path
from playwright.async_api import async_playwright

from .constants import *
from .string import *

def looks_like_linkedin_auth_wall(html: str) -> bool:
  lowered = html.lower()
  return (
    "sign in to linkedin" in lowered
    or "security verification" in lowered
    or "join linkedin" in lowered
    or "let's do a quick security check" in lowered
  )

async def save_logged_in_state(
  login_url: str = "https://www.linkedin.com/login",
  state_file: str = "li_playwright_state.json",
  timeout_ms: int = 180000,
) -> str:
  """Open a visible browser, let the user complete login, then save auth state."""
  async with async_playwright() as p:
    state_path = Path(STATE_PATH) / state_file
    state_path.parent.mkdir(parents=True, exist_ok=True)
    browser = await p.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto(login_url, wait_until="domcontentloaded", timeout=timeout_ms)
    input("Complete login/challenge in browser, then press Enter here...")

    await context.storage_state(path=state_path)
    await browser.close()

  print(f"Saved logged-in browser state to: {state_path}")
  return state_file

def clean_linkedin_link(link: str) -> str:
  return clean_link(link.replace(link[:link.find("linkedin.com")], "https://www."))