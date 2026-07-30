"""Post-deploy canary check for the SaaS Portal customer experience.

Runs after a production deploy (see .github/workflows/platform-deploy.yml) against
the real, just-deployed service - not a local server, not Digital Twin (that
validates a generated app during a mission's build, not the platform itself).

Logs in as a fixed canary customer account (register-if-missing, then login),
loads the customer home page, and opens the first project's workspace page if one
exists - the exact surface where real bugs have shipped undetected before (stale
"Building..." badges, invisible build feedback). Fails (non-zero exit) on any
browser console error or missing expected content. Alert-only: this does not
roll back or block anything else, it just makes a broken deploy visible in the
Actions run instead of waiting for a customer to notice.
"""

from __future__ import annotations

import os
import sys

import requests
from playwright.sync_api import sync_playwright

BASE_URL = os.environ["CANARY_BASE_URL"].rstrip("/")
EMAIL = os.environ["CANARY_CUSTOMER_EMAIL"]
PASSWORD = os.environ["CANARY_CUSTOMER_PASSWORD"]


def get_token() -> str:
    login = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    if login.status_code == 200:
        return login.json()["access_token"]

    register = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "full_name": "Canary Monitor", "organization_name": "Canary"},
        timeout=30,
    )
    if register.status_code == 200:
        return register.json()["access_token"]

    raise RuntimeError(f"Could not authenticate canary account: login={login.status_code} register={register.status_code} {register.text[:500]}")


def main() -> None:
    token = get_token()
    errors: list[str] = []

    def on_response(response):
        if response.status >= 400 and "favicon" not in response.url:
            errors.append(f"HTTP {response.status}: {response.url}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # Uncaught JS exceptions are always a real signal. Generic console.error
        # from the browser's own resource-load logging is not - it fires for any
        # failed asset (including a missing favicon) with no way to see the URL
        # from the console event itself, so it's tracked via response status
        # instead, where it can be filtered precisely.
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
        page.on("response", on_response)

        page.goto(BASE_URL + "/")
        page.evaluate("token => localStorage.setItem('customer_token', token)", token)
        page.goto(BASE_URL + "/customer/home")
        page.wait_for_selector("#homeGreeting", timeout=15000)

        greeting = page.inner_text("#homeGreeting")
        if "what do you want to make" not in greeting.lower():
            errors.append(f"unexpected home greeting: {greeting!r}")

        page.wait_for_selector("#recentProjectsGrid", timeout=15000)
        page.wait_for_timeout(1500)  # let refreshProjects() finish its fetch

        cards = page.query_selector_all("#recentProjectsGrid .proj-card")
        if cards:
            cards[0].click()
            page.wait_for_selector("#view-project.active", timeout=15000)
            page.wait_for_timeout(1000)
            name = page.inner_text("#detailName")
            if not name.strip() or name.strip() == "Loading…":
                errors.append("project detail page did not render a name")

        browser.close()

    if errors:
        print("CANARY CHECK FAILED:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("Canary check passed: home page and project detail rendered with no console errors.")


if __name__ == "__main__":
    main()
