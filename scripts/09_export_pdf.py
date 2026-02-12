from __future__ import annotations

import asyncio
import os
from pathlib import Path
import tempfile

import markdown
from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "reports" / "final"


def md_to_html(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8-sig")
    html_body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <style>
      body {{
        font-family: Arial, sans-serif;
        max-width: 900px;
        margin: 40px auto;
        line-height: 1.5;
      }}
      h1, h2, h3 {{ margin-top: 1.2em; }}
      table {{
        border-collapse: collapse;
        width: 100%;
      }}
      th, td {{
        border: 1px solid #ccc;
        padding: 6px 8px;
      }}
      code {{ background: #f6f8fa; padding: 2px 4px; }}
    </style>
  </head>
  <body>
    {html_body}
  </body>
</html>
"""


async def render_pdf(input_url: str, output_path: Path) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": 1400, "height": 900},
        )
        url = input_url
        if "slides.html" in input_url:
            url = input_url + "?print-pdf"
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.emulate_media(media="screen")
        await page.pdf(path=str(output_path), format="A4", print_background=True)
        await browser.close()


async def main_async() -> None:
    FINAL.mkdir(parents=True, exist_ok=True)

    # 1) Report.md -> HTML -> PDF
    report_md = FINAL / "report.md"
    report_html = md_to_html(report_md)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", dir=FINAL) as tmp:
        tmp.write(report_html.encode("utf-8"))
        tmp_path = Path(tmp.name)
    report_pdf = FINAL / "report.pdf"
    await render_pdf(tmp_path.as_uri(), report_pdf)
    os.unlink(tmp_path)

    # 2) Slides.html -> PDF (Reveal)
    slides_html = FINAL / "slides.html"
    slides_pdf = FINAL / "presentation.pdf"
    await render_pdf(slides_html.as_uri(), slides_pdf)

    print("OK: report.pdf and presentation.pdf saved to reports/final/")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
