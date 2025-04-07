# -------------------------------------------------------------------
# 🐝 BEE JUMBLE SCRAPER
#
# This script powers the Bee Jumble puzzle archive by scraping and
# maintaining a local XML dataset (`bees.xml`) of Spelling Bee-style
# puzzles. It pulls puzzles from two sources:
#
#   1. **sbsolver.com** — Historical and current puzzles, fetched by ID.
#   2. **nytimes.com/puzzles/spelling-bee** — The current day's puzzle.
#
# Key responsibilities:
# -------------------------------------------------------------------
# ✅ Scrapes puzzles for the current month from sbsolver.com, avoiding
#    duplicates and skipping puzzles with identical letter sets to
#    the previous day.
#
# ✅ Scrapes today's puzzle directly from the NYT site (via embedded
#    JavaScript), also skipping duplicates and repeated letter sets.
#
# ✅ Automatically generates and attaches a unique `puzzleid` (UUID4)
#    to every puzzle for reliable identification and linking.
#
# ✅ Stores each puzzle as an XML `<puzzle>` element inside bees.xml,
#    complete with:
#      - `date`, `url`, `letters`, and `puzzleid` attrs
#      - One `<word>` element per word (with length metadata)
#      - One `<letterX>` element (1–7) for each of the 7 letters used,
#        containing a count of words starting with that letter
#
# ✅ Detects and removes duplicate puzzles (by date).
#
# ✅ Ensures consistent formatting and indentation in the XML output.
#
# ✅ Patches any previously saved puzzles that are missing a `puzzleid`.
#
# Notes:
# - Letters are ordered with the common/shared letter first.
# - The XML file is sorted chronologically by puzzle date.
# - The script prints a summary after completion.
#
# Usage:
#   python scraper.py
#
# Dependencies:
#   - requests
#   - beautifulsoup4
#   - tqdm
#
# Output:
#   - bees.xml (created or updated with new puzzle data)
# -------------------------------------------------------------------

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, date
import os
import re
import json
from xml.dom import minidom
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from uuid import uuid4

XML_FILE = "bees.xml"
BASE_URL = "https://www.sbsolver.com/s/"
NYT_URL = "https://www.nytimes.com/puzzles/spelling-bee"

sb_added = 0
nyt_added = 0

def load_existing_dates():
    if not os.path.exists(XML_FILE):
        return set()
    try:
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
        return {p.attrib.get("date") for p in root.findall("puzzle")}
    except ET.ParseError:
        print("⚠️ Warning: bees.xml exists but is not readable.")
        return set()

def indent(elem, level=0):
    i = "\n" + "  " * level
    j = "\n" + "  " * (level + 1)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = j
        for idx, child in enumerate(elem):
            indent(child, level + 1)
            child.tail = i if idx == len(elem) - 1 else j
    else:
        elem.text = elem.text or ''
        elem.tail = elem.tail or i

def find_common_letter(words):
    letter_sets = [set(word) for word in words if word.isalpha()]
    common = set.intersection(*letter_sets) if letter_sets else set()
    return sorted(common)[0] if common else None

def calculate_letters_attribute(words):
    words = [w.upper() for w in words]
    common_letter = find_common_letter(words)
    if not common_letter:
        return None
    all_letters = set("".join(words))
    all_letters.discard(common_letter)
    other_letters = sorted(all_letters)[:6]
    return (common_letter + "".join(other_letters)).upper()

def add_letter_elements(puzzle_el, words, letters):
    from collections import Counter
    first_letter_counts = Counter(word[0] for word in words if word)
    for idx, letter in enumerate(letters):
        tag = f"letter{idx+1}"
        el = ET.SubElement(puzzle_el, tag)
        el.text = str(first_letter_counts.get(letter, 0))

def append_puzzle(root, date_str, url, words):
    puzzle_el = ET.SubElement(root, "puzzle", date=date_str, url=url)
    puzzle_el.set("puzzleid", str(uuid4()))

    for word in words:
        word_el = ET.SubElement(puzzle_el, "word", length=str(len(word)))
        word_el.text = word.upper()

    letter_attr = calculate_letters_attribute(words)
    if letter_attr:
        puzzle_el.set("letters", letter_attr)
        add_letter_elements(puzzle_el, words, letter_attr)

def remove_duplicates(root):
    seen_dates = set()
    unique_puzzles = []
    for puzzle in root.findall("puzzle"):
        date_attr = puzzle.attrib.get("date")
        if date_attr not in seen_dates:
            seen_dates.add(date_attr)
            unique_puzzles.append(puzzle)
    root[:] = unique_puzzles

def get_previous_letters(latest_date):
    if not os.path.exists(XML_FILE):
        return None
    try:
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
        all_puzzles = sorted(root.findall("puzzle"), key=lambda p: p.attrib.get("date", ""))
        prev_puzzle = next((p for p in reversed(all_puzzles) if p.attrib.get("date") < latest_date), None)
        return prev_puzzle.attrib.get("letters") if prev_puzzle is not None else None
    except Exception as e:
        print(f"⚠️ Failed to get previous letters: {e}")
        return None

def fetch_puzzle(i, existing_dates):
    url = f"{BASE_URL}{i}"
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(res.text, "html.parser")
    date_span = soup.find("span", class_="bee-date")
    if not date_span:
        return None
    try:
        date_str = datetime.strptime(date_span.text.replace("Spelling Bee for", "").strip(), "%B %d, %Y").strftime("%Y-%m-%d")
    except:
        return None
    if date_str in existing_dates:
        return None

    words = []
    rows = soup.select("table.bee-set tr")
    for row in rows:
        word_cell = row.find("td", class_="bee-hover")
        if word_cell:
            word = word_cell.get_text(strip=True).upper()
            words.append(word)

    return (date_str, url, words) if words else None

def scrape_sbsolver_month():
    global sb_added
    known_date = datetime(2025, 4, 1)
    known_id = 2520
    today = datetime.today()
    delta_days = (today - known_date).days
    latest_id = known_id + delta_days
    start_id = latest_id - (today.day - 1)

    existing_dates = load_existing_dates()
    print("🔍 Scraping current month from sbsolver.com")

    if os.path.exists(XML_FILE):
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
    else:
        root = ET.Element("spelling_bees")
        tree = ET.ElementTree(root)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_puzzle, i, existing_dates) for i in range(latest_id, start_id - 1, -1)]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Scraping SB Solver"):
            result = future.result()
            if result:
                date_str, url, words = result
                new_letters = calculate_letters_attribute(words)
                previous_letters = get_previous_letters(date_str)
                if new_letters and previous_letters and new_letters == previous_letters:
                    continue
                append_puzzle(root, date_str, url, words)
                sb_added += 1

    remove_duplicates(root)
    root[:] = sorted(root, key=lambda p: p.attrib.get("date", ""))
    indent(root)
    tree.write(XML_FILE, encoding="utf-8", xml_declaration=True)
    print(f"✅ SB Solver: {sb_added} puzzle(s) added.")

def fetch_from_nyt():
    global nyt_added
    today = date.today().strftime("%Y-%m-%d")
    existing_dates = load_existing_dates()
    if today in existing_dates:
        return

    print("🔍 Fetching from NYT site")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(NYT_URL, headers=headers, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"❌ NYT fetch failed: {e}")
        return

    soup = BeautifulSoup(res.text, "html.parser")
    script = next((s.string for s in soup.find_all("script") if s.string and "window.gameData" in s.string), None)
    if not script:
        return

    json_start = script.find("{")
    brace_count = 0
    for i in range(json_start, len(script)):
        if script[i] == "{":
            brace_count += 1
        elif script[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                json_str = script[json_start:i+1]
                break
    else:
        return

    try:
        data = json.loads(json_str)
        words = [w.upper() for w in data.get("today", {}).get("answers", [])]
        if not words:
            return

        new_letters = calculate_letters_attribute(words)
        previous_letters = get_previous_letters(today)
        if new_letters and previous_letters and new_letters == previous_letters:
            print("🛑 Skipping NYT puzzle — letters identical to yesterday.")
            return

        if os.path.exists(XML_FILE):
            tree = ET.parse(XML_FILE)
            root = tree.getroot()
        else:
            root = ET.Element("spelling_bees")
            tree = ET.ElementTree(root)

        append_puzzle(root, today, NYT_URL, words)
        nyt_added += 1
        remove_duplicates(root)
        root[:] = sorted(root, key=lambda p: p.attrib.get("date", ""))
        indent(root)
        tree.write(XML_FILE, encoding="utf-8", xml_declaration=True)
        print(f"✅ NYT puzzle added.")
    except json.JSONDecodeError:
        print("❌ JSON parsing failed.")

def patch_missing_puzzleids(xml_file):
    if not os.path.exists(xml_file):
        print("❌ bees.xml not found.")
        return

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        added = 0
        for puzzle in root.findall("puzzle"):
            if "puzzleid" not in puzzle.attrib:
                puzzle.set("puzzleid", str(uuid4()))
                added += 1
        if added > 0:
            indent(root)
            tree.write(xml_file, encoding="utf-8", xml_declaration=True)
            print(f"🛠️ Patched {added} puzzle(s) with missing puzzleid.")
    except Exception as e:
        print(f"⚠️ Failed to patch puzzleids: {e}")

if __name__ == "__main__":
    scrape_sbsolver_month()
    fetch_from_nyt()
    patch_missing_puzzleids(XML_FILE)

    try:
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
        print("\n📊 Summary:")
        print(f"➕ SB Solver puzzles added: {sb_added}")
        print(f"➕ NYT puzzle added: {nyt_added}")
        print(f"📆 Total puzzles in bees.xml: {len(root)}")
    except Exception as e:
        print(f"⚠️ Could not parse bees.xml to count total puzzles: {e}")
