import asyncio
import logging
import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from telegram import Bot
from playwright.async_api import async_playwright
import constants

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up the bot
bot = Bot(token=constants.token)
chat_id = constants.chat_id

# Scraping targets
scraping_targets = [
    {
        'url': 'https://www.economist.com/topics/finance-and-economics',
        'section_selector': 'a[data-testid="teaser-card-link"]',
    },
    {
        'url': 'https://www.ft.com/lex',
        'section_selector': 'a.js-teaser-heading-link',
    },
    {
        'url': 'https://www.economist.com/topics/business',
        'section_selector': 'a[data-testid="teaser-card-link"]',
    },
    {
        'url': 'https://www.economist.com/topics/economy',
        'section_selector': 'a[data-analytics^="collection_"]',
    },
]

# File to store sent links
sent_links_file = 'sent_links.txt'

# Load sent links from file
def load_sent_links():
    if os.path.exists(sent_links_file):
        with open(sent_links_file, 'r') as f:
            return set(line.strip() for line in f.readlines())
    return set()


# Save a new link to the file
def save_sent_link(link):
    with open(sent_links_file, 'a') as f:
        f.write(link + '\n')


# Initial sent links set
sent_links = load_sent_links()


# Fetch HTML using Playwright. returns rendered HTML for bs4
async def fetch_html(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36")
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        html = await page.content()
        await browser.close()
        return html

# Asynchronous scraping and sending function
async def scrape_and_send():
    global sent_links
    for target in scraping_targets:
        url = target['url']
        section_selector = target['section_selector']

        try:
            html = await fetch_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            sections = soup.select(section_selector)

            if not sections:
                logging.warning(f"No sections found on {url} using selector '{section_selector}'.")
                await bot.send_message(chat_id=chat_id, text=f"No articles found on {url}. Check the HTML selector.")
                continue

            count = 0
            for section in sections:
                if count >= 1:
                    break

                title = section.get_text(strip=True)
                link = section['href'] if section.has_attr('href') else None

                if link and not link.startswith('http'):
                    link = urljoin(url, link)

                if not link or link in sent_links:
                    continue

                sent_links.add(link)
                save_sent_link(link)

                message = f"📰 {title}\n🔗 {link}"
                await bot.send_message(chat_id=chat_id, text=message)
                logging.info(f"Sent: {title}")
                count += 1
                await asyncio.sleep(1)

        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")
            await bot.send_message(chat_id=chat_id, text=f"Error scraping {url}: {e}")


# Execute
if __name__ == '__main__':
    asyncio.run(scrape_and_send())
