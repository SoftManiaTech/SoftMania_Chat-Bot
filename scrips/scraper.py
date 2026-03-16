import sys
import subprocess
import os
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Installing playwright and html2text...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "html2text", "markdownify"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    from playwright.sync_api import sync_playwright

import markdownify

urls = {
    "https://www.softmania.in/": "index.md",
    "https://www.softmania.in/about": "about.md",
    "https://www.softmania.in/splunk-community": "splunk_community.md",
    "https://www.softmania.in/projects": "projects.md",
    "https://www.softmania.in/terms": "terms.md",
    "https://www.softmania.in/refund-policy": "refund_policy.md",
    "https://www.softmania.in/cancellation-policy": "cancellation_policy.md",
    "https://www.softmania.in/contact-us": "contact_us.md",
    "https://www.softmania.in/privacy-policy": "privacy_policy.md",
    "https://splunklab.softmania.in/": "splunklab_index.md",
    "https://bookings.softmania.in/#/services": "bookings.md",
    "https://splunklab.softmania.in/project-course-based-labs": "project_labs.md",
    "https://splunklab.softmania.in/custom-labs": "custom_labs.md",
    "https://splunk.softmania.in/course/softmania-premium#/home?home=true": "premium_bundle.md",
    "https://splunk.softmania.in/clientapp/app/products/explore-products/all-courses": "all_courses.md"
}

output_dir = r"g:\advanced-multi-hop-rag\data\softmania_pages"
os.makedirs(output_dir, exist_ok=True)

print("Starting playwright browser...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    for url, filename in urls.items():
        print(f"Fetching {url}...")
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            time.sleep(3) # Wait for javascript interactions to settle

            # We just want the readable text. Converting outerHTML to markdown 
            # removes the Next.js '__NEXT_DATA__' JSON payload bloat while keeping all visually rendered text.
            body_html = page.evaluate('document.body.outerHTML')
            
            # Using markdownify for clean HTML to MarkDown conversion
            md_text = markdownify.markdownify(body_html, heading_style="ATX", bypass_tables=False)
            
            # Additional cleanup for excessive empty lines
            md_text = "\n".join([line for line in md_text.splitlines() if line.strip() != ""])
            
            markdown_content = f"# Source URL: {url}\n\n{md_text}"
            
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"Saved {filename}")
        except Exception as e:
            print(f"Error on {url}: {e}")
            
    browser.close()
print("All pages exact extraction completed.")
