import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, date
import os
import re

XML_FILE = "bees.xml"
BASE_URL = "https://www.sbsolver.com/s/"
REFERENCE_ID = 2520
REFERENCE_DATE = date(2025, 4, 1)

def calculate_today_id():
    delta_days = (date.today() - REFERENCE_DATE).days
    return REFERENCE_ID + delta_days

def already_scraped(url):
    if not os.path.exists(XML_FILE):
        return False
    try:
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
        return any(p.attrib.get("url") == url for p in root.findall("puzzle"))
    except ET.ParseError:
        print("⚠️ Warning: bees.xml exists but is not readable. Skipping URL check.")
        return False

def append_puzzle(date_str, url, words):
    if os.path.exists(XML_FILE):
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
    else:
        root = ET.Element("spelling_bees")
        tree = ET.ElementTree(root)

    puzzle_el = ET.SubElement(root, "puzzle", date=date_str, url=url)
    for word, length in words:
        word_el = ET.SubElement(puzzle_el, "word", length=str(length))
        word_el.text = word

    tree.write(XML_FILE, encoding="utf-8", xml_declaration=True)
    print(f"✅ Added today's puzzle to bees.xml: {date_str}")

def fetch_today():
    puzzle_id = calculate_today_id()
    url = f"{BASE_URL}{puzzle_id}"
    print(f"🔎 Checking today's puzzle: {url}")

    if already_scraped(url):
        print("📁 Already in bees.xml. Skipping.")
        return

    try:
        res = requests.get(url)
        res.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return

    soup = BeautifulSoup(res.text, "html.parser")

    date_span = soup.find("span", class_="bee-date")
    if not date_span:
        print("⚠️ Date not found on page.")
        return

    date_text = date_span.get_text(strip=True).replace("Spelling Bee for", "").strip()
    try:
        date_obj = datetime.strptime(date_text, "%B %d, %Y")
        date_str = date_obj.strftime("%Y-%m-%d")
    except ValueError:
        print(f"⚠️ Could not parse date: {date_text}")
        return

    words = []
    for row in soup.select("table.bee-set tr"):
        word_td = row.find("td", class_="bee-hover")
        len_td = row.find("td", class_="bee-set-num")
        if word_td and len_td:
            word = word_td.get_text(strip=True)
            length = len_td.get_text(strip=True)
            words.append((word, int(length)))

    if words:
        append_puzzle(date_str, url, words)
    else:
        print("⚠️ No words found.")

if __name__ == "__main__":
    fetch_today()
