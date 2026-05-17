import json
import requests
from bs4 import BeautifulSoup

ROUTES = ["/", "/form", "/login", "/dashboard", "/api/data", "/api/users", "/health"]

SEVERITY_WEIGHT = {
    "CRITICAL": 3.0,
    "HIGH":     2.0,
    "MEDIUM":   1.0,
    "LOW":      0.5,
}

def _make_error(route, etype, message, severity):
    return {
        "route":    route,
        "type":     etype,
        "message":  message,
        "severity": severity,
        "weight":   SEVERITY_WEIGHT[severity],
    }

def _tally(errors):
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for e in errors:
        counts[e["severity"]] += 1
    total = sum(e["weight"] for e in errors)
    return total, counts

class SearchEnv:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # PRIMARY — Playwright
    # ------------------------------------------------------------------
    def _playwright_scan(self):
        from playwright.sync_api import sync_playwright, Error as PWError

        errors = []
        routes_checked = 0

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context()

            for route in ROUTES:
                url = self.base_url + route
                page = context.new_page()

                console_errors = []
                page_errors    = []
                network_404s   = []

                # Listeners — must be attached before goto
                page.on("console",
                    lambda msg: console_errors.append(msg.text)
                    if msg.type == "error" else None)

                page.on("pageerror",
                    lambda exc: page_errors.append(str(exc)))

                def handle_route(req, resp_container=network_404s):
                    try:
                        response = req.fetch()
                        if response.status == 404:
                            resp_container.append(req.url)
                        req.fulfill(response=response)
                    except Exception:
                        req.continue_()

                page.route("**/*", handle_route)

                try:
                    response = page.goto(url, timeout=8000,
                                         wait_until="networkidle")
                    routes_checked += 1
                    status = response.status if response else 0

                    # HTTP status checks
                    if status == 500:
                        errors.append(_make_error(route, "http_500",
                            f"Server error HTTP 500", "CRITICAL"))
                    elif status == 404:
                        errors.append(_make_error(route, "http_404",
                            f"Route not found HTTP 404", "HIGH"))

                    # JS / page errors
                    for exc in page_errors:
                        errors.append(_make_error(route, "pageerror",
                            exc, "CRITICAL"))

                    # Console errors
                    for msg in console_errors:
                        errors.append(_make_error(route, "console_error",
                            msg, "MEDIUM"))

                    # CSS check
                    try:
                        css_count = page.evaluate("document.styleSheets.length")
                        if css_count == 0:
                            errors.append(_make_error(route, "css_missing",
                                "No stylesheets loaded", "MEDIUM"))
                    except Exception:
                        pass

                    # Network 404s
                    for bad_url in network_404s:
                        errors.append(_make_error(route, "network_404",
                            f"Resource 404: {bad_url}", "LOW"))

                except Exception:
                    # Connection error — skip this route silently
                    pass
                finally:
                    page.close()

            browser.close()

        return errors, routes_checked

    # ------------------------------------------------------------------
    # FALLBACK — requests + BeautifulSoup
    # ------------------------------------------------------------------
    def _requests_scan(self):
        errors = []
        routes_checked = 0

        for route in ROUTES:
            url = self.base_url + route
            try:
                resp = requests.get(url, timeout=6)
                routes_checked += 1
                status = resp.status_code

                if status == 500:
                    errors.append(_make_error(route, "http_500",
                        "Server error HTTP 500", "CRITICAL"))
                elif status == 404:
                    errors.append(_make_error(route, "http_404",
                        "Route not found HTTP 404", "HIGH"))

                # BeautifulSoup — broken img src
                if "text/html" in resp.headers.get("Content-Type", ""):
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for img in soup.find_all("img"):
                        src = img.get("src", "")
                        if not src or src.strip() == "":
                            errors.append(_make_error(route, "broken_img",
                                f"Image tag with empty/missing src", "LOW"))
                        else:
                            # Check if the image itself 404s
                            img_url = (src if src.startswith("http")
                                       else self.base_url + "/" + src.lstrip("/"))
                            try:
                                ir = requests.get(img_url, timeout=4)
                                if ir.status_code == 404:
                                    errors.append(_make_error(route, "img_404",
                                        f"Image 404: {src}", "LOW"))
                            except Exception:
                                pass

            except Exception:
                # Connection refused / timeout — skip silently
                pass

        return errors, routes_checked

    # ------------------------------------------------------------------
    # PUBLIC — scan()
    # ------------------------------------------------------------------
    def scan(self) -> dict:
        scanner_used = "playwright"
        errors = []
        routes_checked = 0

        try:
            errors, routes_checked = self._playwright_scan()
        except Exception:
            scanner_used = "requests_fallback"
            try:
                errors, routes_checked = self._requests_scan()
            except Exception:
                pass

        total_score, counts = _tally(errors)

        return {
            "errors":         errors,
            "total_score":    round(total_score, 2),
            "routes_checked": routes_checked,
            "critical_count": counts["CRITICAL"],
            "high_count":     counts["HIGH"],
            "medium_count":   counts["MEDIUM"],
            "low_count":      counts["LOW"],
            "scanner_used":   scanner_used,
        }


if __name__ == "__main__":
    import sys
    env = SearchEnv(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000")
    print(json.dumps(env.scan(), indent=2))
