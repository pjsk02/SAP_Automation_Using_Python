
# magaya_download.py
import os, time
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, expect

load_dotenv()
BASE_URL     = "https://tracking.magaya.com/?orgname=37508#livetrack"
USERNAME     = "lucyboviet"
PASSWORD     = "PASSWORD"
TIMEFRAME    = "TIMEFRAME"
VIEW         = "Annu"
ROWS         = int("1000")
DOWNLOAD_DIR = Path(("DOWNLOAD_DIR") or (Path.cwd() / "downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

def text_input(page, label_text, value):
    """
    Fills an input near a visible label or placeholder.
    Adjust this helper if your login inputs differ.
    """
    # Try accessible placeholder first
    loc = page.get_by_placeholder(label_text)
    if not loc.count():
        # Fallback: label -> input
        loc = page.locator(f"label:has-text('{label_text}')").locator("xpath=following::input[1]")
    loc.fill(value)

def main(headless=True):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, channel="msedge" if not headless else None)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # 1) Login page
        page.goto(BASE_URL, wait_until="domcontentloaded")

        # Your login fields may not have placeholders; adapt as needed:
        # Example selectors commonly work on ExtJS/ports:
        page.locator("input[name='username']").fill(USERNAME)
        page.locator("input[name='password']").fill(PASSWORD)

        # Try generic guesses first; if they fail, fall back to indexed inputs:
        try:
            page.locator("input[type='text'], input[type='email']").first.fill(USERNAME)
            page.locator("input[type='password']").first.fill(PASSWORD)
        except:
            # Fallback: fill by tabindex or data-qa if present
            page.locator("xpath=(//input)[1]").fill(USERNAME)
            page.locator("xpath=(//input[@type='password'])[1]").fill(PASSWORD)

        # Click Login
        # Prefer role/text; ExtJS buttons often render as <a role="button"><span>Login</span></a>
        login_btn = page.get_by_role("button", name=lambda n: n and "login" in n.lower())
        if not login_btn.count():
            login_btn = page.locator("//a[.//span[normalize-space()='Login'] or normalize-space()='Login']")
        login_btn.click()
        page.wait_for_load_state("networkidle")

        # 2) Click Shipments
        # Your PAD step clicked “uiText_Shipments”
        shipments = page.get_by_role("link", name=lambda n: n and "shipments" in n.lower())
        if not shipments.count():
            shipments = page.locator("//a[.//span[normalize-space()='Shipments'] or normalize-space()='Shipments']")
        shipments.click()
        page.wait_for_load_state("networkidle")

        # 3) Choose time frame (this mimics your OK/Cancel branch)
        # Open the time-frame dropdown (uiDropDown_TimeFrame)
        # We try a few options: by label, aria, or contains text
        tf_drop = page.get_by_role("combobox").filter(has_text="Time")
        if not tf_drop.count():
            tf_drop = page.locator("//input[contains(@id,'TimeFrame') or contains(@name,'TimeFrame') or contains(@aria-label,'Time')]")
        try:
            tf_drop.click()
            page.keyboard.type(TIMEFRAME)
            page.keyboard.press("Enter")
        except:
            pass  # If the page is already at correct timeframe, no-op

        # Click Refresh (uiBtn_Refresh)
        refresh_btn = page.get_by_role("button", name=lambda n: n and "refresh" in n.lower())
        if not refresh_btn.count():
            refresh_btn = page.locator("//a[.//span[normalize-space()='Refresh'] or normalize-space()='Refresh']")
        refresh_btn.click()
        page.wait_for_load_state("networkidle")

        # 4) Select View (uiCmb_ViewSelect with "Annu")
        view_input = page.locator("//input[contains(@id,'ViewSelect') or contains(@name,'ViewSelect') or contains(@aria-label,'View')]")
        if view_input.count():
            view_input.click()
            page.keyboard.type(VIEW)
            page.keyboard.press("Enter")

        # 5) Set 1000 records (UIText_1000Recs)
        rows_input = page.locator("//input[contains(@id,'1000') or contains(@placeholder,'1000') or contains(@aria-label,'records') or contains(@id,'Rows')]")
        if not rows_input.count():
            # try any numeric input in a paging toolbar
            rows_input = page.locator("//div[contains(@id,'paging') or contains(@id,'toolbar')]//input[@type='text' or @type='number']")
        try:
            rows_input.click()
            page.keyboard.press("Control+A")
            page.keyboard.type(str(ROWS))
            page.keyboard.press("Enter")
        except:
            pass

        # Refresh again (as in your PAD)
        try:
            refresh_btn.click()
            page.wait_for_load_state("networkidle")
        except:
            pass

        # 6) Actions → Export… → Download
        # Actions
        actions_btn = page.get_by_role("button", name=lambda n: n and "actions" in n.lower())
        if not actions_btn.count():
            actions_btn = page.locator("//a[.//span[normalize-space()='Actions'] or normalize-space()='Actions']")
        actions_btn.click()

        # Export...
        export_item = page.get_by_role("menuitem", name=lambda n: n and "export" in n.lower())
        if not export_item.count():
            export_item = page.locator("//a[.//span[contains(normalize-space(),'Export')] or contains(normalize-space(),'Export')]")
        export_item.click()

        # Now a modal/popup with a **Download** button usually appears.
        # Capture download robustly:
        with page.expect_download() as dl_info:
            download_btn = page.get_by_role("button", name=lambda n: n and "download" in n.lower())
            if not download_btn.count():
                download_btn = page.locator("//a[.//span[normalize-space()='Download'] or normalize-space()='Download']")
            download_btn.click()
        download = dl_info.value

        # Save with deterministic name
        suggested = download.suggested_filename or "export.csv"
        final_path = DOWNLOAD_DIR / f"{int(time.time())}_{suggested}"
        download.save_as(str(final_path))
        print(f"Saved → {final_path}")

        context.close()
        browser.close()

if __name__ == "__main__":
    # Run headed first to confirm selectors, then set headless=True
    main(headless=False)
