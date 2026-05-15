import requests

from dataclasses import dataclass
from scrapy.http import HtmlResponse

@dataclass
class ScrapeResult:
  url: str
  title: str
  content: str
  html: str

def __scrape_with_scrapy_selector(url: str, timeout: int) -> ScrapeResult:
  """
  Use Scrapy's selector engine to parse the page.
  This is lighter than launching a full Scrapy crawl and works well for single-page scraping.
  """
  headers = {
    "User-Agent": (
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/148.0.0.0 Safari/537.36"
    )
  }

  response = requests.get(url, timeout = timeout, headers = headers)
  response.raise_for_status()

  html_response = HtmlResponse(url = url, body = response.content, encoding = "utf-8")
  title = (html_response.css("title::text").get() or "").strip()

  texts = [t.strip() for t in html_response.xpath("//body//text()[normalize-space()]").getall()]
  content = " ".join(t for t in texts if t)

  return ScrapeResult(url = url, title=title, content = content, html = response.text)

def scrape_website(
  url: str,
  timeout: int = 20
) -> ScrapeResult:
  """
  Scrape a webpage and return its title, text content, and raw HTML.

  Args:
    url: Target webpage URL.
    timeout: HTTP timeout (seconds) for request-based backends.

  Returns:
    ScrapeResult with URL, page title, extracted text content, and full HTML.
  """
  return __scrape_with_scrapy_selector(url=url, timeout=timeout)

def is_element_hidden(el, hidden_divs):
  """Check if the element or any of its ancestors are in hidden_divs."""
  for parent in [el] + list(el.parents):
    if parent in hidden_divs:
      return True
  return False