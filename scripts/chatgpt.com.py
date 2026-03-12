"""
Script to interact with chatgpt.com using Playwright.
"""

import json
import os
import sys
import time


from playwright.sync_api import sync_playwright, Page

import conflog

# Initialize logger using conflog
c_log = conflog.Conflog(
    conf_dict={
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    }
)
logger = c_log.get_logger(__name__)


def wait_for_response(
    page: Page,
    timeout_seconds: float = 60.0,
    stability_seconds: float = 1.5,
) -> str:
    """Wait for the assistant response to stabilize and return it."""
    locators = page.locator('[data-message-author-role="assistant"]')
    start_time = time.time()
    last_text = None
    last_change_time = None

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            logger.warning("Timed out waiting for assistant response.")
            break

        count = locators.count()
        if count == 0:
            time.sleep(0.5)
            continue

        current_text = locators.nth(count - 1).inner_text()
        now = time.time()

        if last_text is None or current_text != last_text:
            last_text = current_text
            last_change_time = now
        else:
            if (
                last_change_time is not None
                and (now - last_change_time) >= stability_seconds
            ):
                break

        time.sleep(0.5)

    if locators.count() > 0:
        logger.info("Received response.")
        return locators.last.inner_text()

    logger.warning("No response found, returning empty JSON.")
    return "{}"


def parse_response(raw_response: str) -> dict:
    """Clean and parse the raw response into JSON."""
    clean_response = raw_response.strip()
    if clean_response.startswith("```json"):
        clean_response = clean_response[7:]
    if clean_response.endswith("```"):
        clean_response = clean_response[:-3]

    clean_response = clean_response.strip()

    try:
        return json.loads(clean_response)
    except json.JSONDecodeError:
        logger.error("Failed to parse response as JSON. Saving raw response anyway.")
        return {"raw_response": clean_response}


def save_response(base_dir: str, parsed_json: dict) -> None:
    """Save the parsed JSON to the data directory."""
    data_path = os.path.join(base_dir, "data", "chatgpt.com.json")
    with open(data_path, "w", encoding="utf-8") as file:
        json.dump(parsed_json, file, indent=4)
    logger.info("Extraction finished. Data saved.")


def interact_with_chatgpt(url: str, prompt: str) -> str:
    """Launch browser, navigate to URL, send prompt, and return the response."""
    latest_response = "{}"
    with sync_playwright() as playwright:
        logger.info("Launching browser...")
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        logger.info("Navigating to %s", url)
        try:
            page.goto(url, wait_until="load")
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Failed to navigate: %s", error)
            sys.exit(1)

        logger.info("Waiting for prompt textarea...")
        textarea_selector = "#prompt-textarea"

        try:
            page.wait_for_selector(textarea_selector, timeout=15000)
            page.fill(textarea_selector, prompt)

            page.click('[data-testid="send-button"]')
            logger.info("Prompt sent. Waiting for response...")

            latest_response = wait_for_response(page)

        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error interacting with page: %s", error)

        finally:
            browser.close()

    return latest_response


def main() -> None:
    """Main function to run the ChatGPT extraction."""
    logger.info("Starting up ChatGPT extraction job.")

    base_dir = os.path.dirname(os.path.dirname(__file__))

    # Load conf
    conf_path = os.path.join(base_dir, "conf", "llms.json")
    with open(conf_path, "r", encoding="utf-8") as file:
        conf = json.load(file)

    url = conf.get("chatgpt.com", {}).get("url", "https://chatgpt.com")

    # Load prompt
    prompt_path = os.path.join(base_dir, "prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as file:
        prompt = file.read()

    # Execution
    raw_response = interact_with_chatgpt(url, prompt)
    parsed_json = parse_response(raw_response)
    save_response(base_dir, parsed_json)


if __name__ == "__main__":
    main()
