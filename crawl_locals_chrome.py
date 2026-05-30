from contextlib import ExitStack
import os
import time, random
import json
from playwright.sync_api import sync_playwright

def sleep():
    t = random.uniform(3, 7)
    print(f"Sleeping {t} seconds...")
    time.sleep(t)
    print("Done")

if not os.path.isdir("dumps"):
    sys.exit(1)

def save_page(page):
    fn = int(time.time() * 1000)
    if os.path.exists(f"dumps/{fn}.json"):
        sys.exit(1)
    page.pdf(path=f"dumps/{fn}.pdf", print_background=True, landscape=False)
    with open(f"dumps/{fn}.html", "w") as f:
        f.write(page.content())
    with open(f"dumps/{fn}.json", "w") as f:
        json.dump({
            "url": page.url,
        }, f)

input("Clear the browser cache and press enter")

page_urls = set()
with open('urllist.txt') as f:
    page_urls.update(l.strip() for l in f)
page_with_no_urls = 0

with ExitStack() as stack:
    p, f = [
        stack.enter_context(c)
        for c in [sync_playwright(), open('urllist.txt', 'a', buffering=1)]
    ]
    chromium = p.chromium
    # Connect to the running browser via CDP
    browser = chromium.connect_over_cdp("http://localhost:9222")
    # Use an existing context/page or create new
    contexts = browser.contexts
    context = contexts[0] if contexts else browser.new_context()
    pages = context.pages
    page = pages[0] if pages else context.new_page()

    page.route("**/*", lambda route, request: route.continue_(headers={**request.headers, "Cache-Control": "no-cache"}))
    page.goto("https://scottadams.locals.com/member/ScottAdamsSays", wait_until="domcontentloaded")
    while True:
        sleep()
        save_page(page)
        urls = [
            a.get_attribute("href")
            for a in page.query_selector_all("a.post-link")]
        urls = [u for u in urls if u and u not in page_urls]

        if urls:
            page_with_no_urls = 0
            for u in urls:
                f.write(u + "\n")
                f.flush()
                page_urls.add(u)
        else:
            page_with_no_urls += 1
            print(f"Page with no new URLs: {page_with_no_urls}")
            if page_with_no_urls >= 10:
                break

        locator = page.locator('li.prevnext >> a:has-text("Next")')
        if locator.count() == 0:
            print("No next link")
            break
        elif locator.count() == 1:
            print("Going to next page")
            with page.expect_navigation(wait_until="load", timeout=10000):
                locator.first.click()
        else:
            print(f"Unexpected count: {locator.count()}")
            sys.exit(1)

    browser.close()