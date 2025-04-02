import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import os
import re
from xml.dom import minidom

XML_FILE = "bees.xml"
BASE_URL = "https://www.sbsolver.com/s/"

def load_existing_ids():
    existing_ids = set()
    if os.path.exists(XML_FILE):
        try:
            tree = ET.parse(XML_FILE)
            root = tree.getroot()
            for puzzle in root.findall("puzzle"):
                url = puzzle.attrib.get("url", "")
                match = re.search(r"/s/(\d+)", url)
                if match:
                    existing_ids.add(int(match.group(1)))
        except ET.ParseError:
            print("⚠️ Could not parse existing bees.xml, starting fresh.")
    return existing_ids

def scrape_range(start_id, end_id):
    existing_ids = load_existing_ids()
    ids_to_fetch = [i for i in range(start_id, end_id + 1) if i not in existing_ids]

    if not ids_to_fetch:
        print("🎉 All puzzles in this range already exist.")
        return

    print(f"📦 Fetching {len(ids_to_fetch)} missing puzzle(s): {ids_to_fetch[:10]}{'...' if len(ids_to_fetch) > 10 else ''}")

    if os.path.exists(XML_FILE):
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
    else:
        root = ET.Element("spelling_bees")
        tree = ET.ElementTree(root)

    for i in ids_to_fetch:
        url = f"{BASE_URL}{i}"
        print(f"🔎 Fetching: {url}")
        try:
            res = requests.get(url)
            res.raise_for_status()
        except Exception as e:
            print(f"❌ Failed to fetch {url}: {e}")
            continue

        soup = BeautifulSoup(res.text, "html.parser")

        date_span = soup.find("span", class_="bee-date")
        if not date_span:
            print(f"⚠️ No date found for {url}")
            continue

        date_text = date_span.get_text(strip=True).replace("Spelling Bee for", "").strip()
        try:
            date_obj = datetime.strptime(date_text, "%B %d, %Y")
            date_str = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            print(f"⚠️ Unreadable date on {url}: {date_text}")
            continue

        puzzle_el = ET.SubElement(root, "puzzle", date=date_str, url=url)

        rows = soup.select("table.bee-set tr")
        for row in rows:
            word_cell = row.find("td", class_="bee-hover")
            length_cell = row.find("td", class_="bee-set-num")
            if word_cell and length_cell:
                word = word_cell.get_text(strip=True)
                length = length_cell.get_text(strip=True)
                word_el = ET.SubElement(puzzle_el, "word", length=length)
                word_el.text = word

        time.sleep(0.25)

    # ✅ Sort puzzles by puzzle ID from the URL
    def get_puzzle_id(p):
        match = re.search(r"/s/(\d+)", p.attrib.get("url", ""))
        return int(match.group(1)) if match else 0

    root[:] = sorted(root, key=get_puzzle_id)

    # ✅ Pretty-print with indentation using minidom
    xml_string = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(xml_string)
    pretty_xml_as_string = parsed.toprettyxml(indent="  ")

    with open(XML_FILE, "w", encoding="utf-8") as f:
        f.write(pretty_xml_as_string)

    print("✅ Done! bees.xml updated with new entries (sorted + pretty).")

if __name__ == "__main__":
    try:
        start = int(input("Enter start puzzle ID (e.g., 1): "))
        end = int(input("Enter end puzzle ID (e.g., 2520): "))
        if start > end or start < 1:
            raise ValueError
        scrape_range(start, end)
    except ValueError:
        print("❌ Invalid range. Please enter valid integers, with start ≤ end and ≥ 1.")
