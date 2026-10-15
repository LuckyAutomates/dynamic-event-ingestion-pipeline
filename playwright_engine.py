import json
import os

import psycopg2
import requests
from psycopg2.extras import execute_batch
from playwright.sync_api import sync_playwright


scraped_items = []


def save_quotes(items):
    if "DB_PASSWORD" not in os.environ:
        raise RuntimeError("DB_PASSWORD environment variable is required.")

    db_password = os.environ.get("DB_PASSWORD").strip()
    if not db_password:
        raise RuntimeError("DB_PASSWORD must not be empty.")

    db_params = {
        "host": "127.0.0.1",
        "port": 5432,
        "dbname": "postgres",
        "user": "postgres",
        "password": db_password,
        "connect_timeout": 10,
    }

    records = [
        {
            "source_channel": "https://toscrape.com",
            "payload_type": "QUOTE_LOG",
            "structured_data": json.dumps(
                {
                    "text": item["quote_text"],
                    "author": item["author"],
                    "page_number": item["page_number"],
                }
            ),
        }
        for item in items
    ]

    connection = None
    cursor = None

    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()

        if records:
            execute_batch(
                cursor,
                """
                INSERT INTO production_ingest
                    (source_channel, payload_type, structured_data)
                VALUES
                    (%(source_channel)s, %(payload_type)s, %(structured_data)s)
                """,
                records,
            )

        connection.commit()
        print(f"[DATABASE] Inserted {len(records)} quotes.")

    except Exception:
        if connection is not None:
            connection.rollback()
        print("[DATABASE ERROR] Ingest failed; transaction rolled back.")
        raise

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


def extract_quotes():
    print("[INITIATED] Starting Playwright...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = None

        try:
            context = browser.new_context()
            page = context.new_page()

            print("[ROUTING] Opening Quotes to Scrape...")
            page.goto(
                "https://quotes.toscrape.com/",
                wait_until="domcontentloaded",
            )
            page.locator(".quote").first.wait_for()

            page_number = 1

            while True:
                print(f"\n--- PAGE {page_number} ---")

                quote_blocks = page.locator(".quote")
                block_count = quote_blocks.count()

                for i in range(block_count):
                    quote = quote_blocks.nth(i)
                    scraped_items.append(
                        {
                            "text": quote.locator(".text").inner_text(),
                            "author": quote.locator(".author").inner_text(),
                        }
                    )

                next_button = page.locator("li.next > a")

                if next_button.count() == 0:
                    print(f"\n[FINISHED] Reached the last page ({page_number}).")
                    break

                next_button.click()
                page.locator(".quote").first.wait_for()
                page_number += 1

        finally:
            try:
                if context is not None:
                    context.close()
            finally:
                browser.close()

    payload = {"quotes": scraped_items}
    response = requests.post(
        "http://127.0.0.1:8000/ingest",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    print(response.text)


if __name__ == "__main__":
    extract_quotes()