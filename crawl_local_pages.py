import os
import json
from contextlib import ExitStack
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
import time, random

if not os.path.isdir("dumps"):
    sys.exit(1)

def sleep():
    t = random.uniform(3, 7)
    print(f"Sleeping {t} seconds...")
    time.sleep(t)
    print("Done")

def wait_for_idle(page, wait_timeout=30000):
    try:
        print('Waiting for network idle')
        page.wait_for_load_state("networkidle", timeout=wait_timeout)
    except PlaywrightTimeoutError:
        time.sleep(0.2)

    # Wait for short DOM stabilization (no mutations for 200ms), up to 2s
    try:
        print('Waiting for dom to stabilizie')
        page.wait_for_function(
            """
            () => {
                if (!window.__lastMutationTime) {
                window.__lastMutationTime = Date.now();
                const obs = new MutationObserver(() => { window.__lastMutationTime = Date.now(); });
                obs.observe(document, {childList: true, subtree: true, attributes: true});
                }
                return (Date.now() - window.__lastMutationTime) > 200;
            }
            """,
            timeout=2000
        )
    except PlaywrightTimeoutError:
        pass


def last_n_all_equal(lst: list, n: int = 10) -> bool:
    if not lst:
        return False
    if len(lst) < n:
        return False
    tail = lst[-n:]
    return all(x == tail[0] for x in tail)


def click_history_until_gone(page, click_timeout=30000, wait_timeout=30000):
    handle = page.query_selector('#chat-window')
    if not handle:
        print('No chat found')
        return
    print('Waiting a little bit for chat to load')
    time.sleep(random.uniform(10, 20))
    chat_message_count = []
    while True:
        handle = page.query_selector('#chat-window')
        page.evaluate("(el) => el.scrollTop = 0", handle)
        time.sleep(0.2)

        handle = page.query_selector('.chatinput__history')
        if not handle:
            print('No load button')
            return
        display = page.evaluate("(el) => getComputedStyle(el).display", handle)
        if display == 'none':
            print('Load history is hidden, stopping')
            return

        page.evaluate("(el) => el.scrollIntoView({block: 'center', inline: 'center', behavior: 'auto'})", handle)
        try:
            print('Clicking on load history')
            handle.click(timeout=click_timeout)
        except PlaywrightTimeoutError:
            page.evaluate("(el) => el.click()", handle)

        wait_for_idle(page, wait_timeout=wait_timeout)
        page.evaluate("(el) => el.scrollTop = 0", handle)

        print('Sleeping a little bit')
        time.sleep(random.uniform(1, 3))

        message_count = page.locator("#chat-history .pmessage").count()
        print(f"Message count: {message_count}")
        chat_message_count.append(message_count)
        if last_n_all_equal(chat_message_count, n=10):
            print("Chat message count didn't change the last 10 times, stopping")
            return

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

urls_done = set()
with open('urllist-done.txt') as f:
    urls_done.update(l.strip() for l in f)

with open('urllist.txt') as f:
    urls = [u.strip() for u in f if u.strip() not in urls_done]

input("Clear the browser cache and press enter")

with ExitStack() as stack:
    p, f_done, f_videos = [
        stack.enter_context(c)
        for c in [
            sync_playwright(),
            open('urllist-done.txt', 'a', buffering=1),
            open('urllist-videos.txt', 'a', buffering=1),
        ]
    ]

    chromium = p.chromium
    # Connect to the running browser via CDP
    browser = chromium.connect_over_cdp("http://localhost:9222")
    # Use an existing context/page or create new
    contexts = browser.contexts
    context = contexts[0] if contexts else browser.new_context()
    pages = context.pages
    page = pages[0] if pages else context.new_page()

    #page.route("**/*", lambda route, request: route.continue_(headers={**request.headers, "Cache-Control": "no-cache"}))

    for i, url in enumerate(urls):
        print(f"[{i+1}/{len(urls)}] {url}")
        if url in urls_done:
            print('Already processed, skipping')
            continue

        while True:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=10000)
                wait_for_idle(page)
                break
            except PlaywrightError as e:
                print('Playwright error: ' + str(e))
                sleep()
                print('Retry')

        click_history_until_gone(page)

        save_page(page)

        if page.query_selector('.media.video'):
            print('This is a video')
            f_videos.write(url + "\n")
            f_videos.flush()

        photo = page.query_selector('.on-clickable.photo')
        if photo:
            print('Photo found')
            photo.click()
            wait_for_idle(page)
            save_page(page)

        f_done.write(url + "\n")
        f_done.flush()
