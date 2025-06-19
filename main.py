import requests
from bs4 import BeautifulSoup
import constants
from telegram import Bot
import logging
import asyncio
import os

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up the bot
bot = Bot(token=constants.token)
chat_id = constants.chat_id

# Scraping targets
scraping_targets = [
    {
        'url': 'https://www.economist.com/topics/finance-and-economics',
        'section_selector': 'a[data-test-id="teaser-card-link"]',
    },
    {
        'url': 'https://www.ft.com/lex',
        'section_selector': 'a.js-teaser-heading-link', 
    },
    {
        'url': 'https://www.economist.com/topics/business',
        'section_selector': 'a[data-test-id="teaser-card-link"]',
    },
    {
        'url': 'https://www.economist.com/topics/economy', # Different HTML template/page structure. Would have to define a function to try 
        'section_selector': 'a[data-analytics^="collection_"]', # or incorporate some intelligence to find the css selectors without me
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

# Asynchronous scraping and sending function
async def scrape_and_send():
    global sent_links
    for target in scraping_targets:
        url = target['url']
        section_selector = target['section_selector']

        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            print(f"URL: {url}, Status Code: {response.status_code}")
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
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
                print('testing:',link)
                if link and not link.startswith('http'):
                    link = requests.compat.urljoin(url, link)

                if not link or link in sent_links:
                    continue
                print('after:',link)
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
