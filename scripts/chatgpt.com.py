"""
Script to interact with chatgpt.com using Playwright.
"""

import json
import logging
import os
import sys
import time

from playwright.sync_api import sync_playwright

import conflog

# Initialize logger using conflog
c_log = conflog.Conflog(
    conf_dict={
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    }
)
logger = c_log.get_logger(__name__)


def main() -> None:
    """Main function to run the ChatGPT extraction."""
    logger.info("Starting up ChatGPT extraction job.")

    # Load conf
    base_dir = os.path.dirname(os.path.dirname(__file__))
    conf_path = os.path.join(base_dir, "conf", "llms.json")
    with open(conf_path, "r", encoding="utf-8") as file:
        conf = json.load(file)

    url = conf.get("chatgpt.com", {}).get("url", "https://chatgpt.com")

    # Load prompt
    prompt_path = os.path.join(base_dir, "prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as file:
        prompt = file.read()

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

        latest_response = "{}"
        try:
            page.wait_for_selector(textarea_selector, timeout=15000)
            page.fill(textarea_selector, prompt)

            page.click('[data-testid="send-button"]')
            logger.info("Prompt sent. Waiting for response...")

            time.sleep(20)  # Wait for LLM to stream response

            # Attempt to extract response
            locators = page.locator('[data-message-author-role="assistant"]')
            responses = locators.all_inner_texts()
            if responses:
                latest_response = responses[-1]
                logger.info("Received response.")
            else:
                logger.warning("No response found, returning empty JSON.")

        except Exception as error:  # pylint: disable=broad-except
            logger.error("Error interacting with page: %s", error)

        finally:
            browser.close()

        # Parse response as JSON
        clean_response = latest_response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]

        clean_response = clean_response.strip()

        try:
            parsed_json = json.loads(clean_response)
        except json.JSONDecodeError:
            logger.error("Failed to parse response as JSON. Saving raw response anyway.")
            parsed_json = {"raw_response": clean_response}

        data_path = os.path.join(base_dir, "data", "chatgpt.com.json")
        with open(data_path, "w", encoding="utf-8") as file:
            json.dump(parsed_json, file, indent=4)
        logger.info("Extraction finished. Data saved.")


if __name__ == "__main__":
    main()
