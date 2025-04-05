# -------------------------------------------------------------------
# 🧩 Bee Jumble Pipeline: Scrape → Jumble → Post
#
# Dependencies:
#   - requests
#   - beautifulsoup4
#   - tqdm
#   - lxml (for faster XML parsing, optional)
#
# Files this script creates or uses:
#   - bees.xml (scraped puzzles)
#   - jumbledbees.xml (scrambled for public use)
#   - index.htm (your game interface — must exist in directory)
#
# Output: Uploads index.htm + jumbledbees.xml to remote FTP server
# -------------------------------------------------------------------

# ========== IMPORTS ========== #
import os
import xml.etree.ElementTree as ET
import requests
import random
import json
from bs4 import BeautifulSoup
from datetime import datetime, date
from collections import Counter
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from ftplib import FTP

# ========== CONFIG ========== #
XML_FILE = "bees.xml"
TARGET_FILE = "jumbledbees.xml"
INDEX_HTML = "index.htm"

FTP_HOST = "ftp.tii.ezv.temporary.site"
FTP_PORT = 21
FTP_USER = "beejumble@tii.ezv.temporary.site"
FTP_PASS = "{jTm-6zL$r_h"

BASE_URL = "https://www.sbsolver.com/s/"
NYT_URL = "https://www.nytimes.com/puzzles/spelling-bee"

# ========== UTILITY ========== #
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

# ========== SCRAPER ========== #
def load_existing_dates():
    if not os.path.exists(XML_FILE):
        return set()
    try:
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
        return {p.attrib.get("date") for p in root.findall("puzzle")}
    except ET.ParseError:
        print("⚠️ bees.xml is unreadable.")
        return set()

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
    first_letter_counts = Counter(word[0] for word in words if word)
    for idx, letter in enumerate(letters):
        tag = f"letter{idx+1}"
        el = ET.SubElement(puzzle_el, tag)
        el.text = str(first_letter_counts.get(letter, 0))

def append_puzzle(root, date_str, url, words):
    puzzle_el = ET.SubElement(root, "puzzle", date=date_str, url=url)
    for word in words:
        word_el = ET.SubElement(puzzle_el, "word", length=str(len(word)))
        word_el.text = word.upper()
    letter_attr = calculate_letters_attribute(words)
    if letter_attr:
        puzzle_el.set("letters", letter_attr)
        add_letter_elements(puzzle_el, words, letter_attr)

def scrape_sbsolver_month():
    known_date = datetime(2025, 4, 1)
    known_id = 2520
    today = datetime.today()
    start_of_month = today.replace(day=1)
    delta_days = (today - known_date).days
    latest_id = known_id + delta_days
    start_id = latest_id - (today.day - 1)

    existing_dates = load_existing_dates()
    print("🔍 Scraping sbsolver.com")

    if os.path.exists(XML_FILE):
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
    else:
        root = ET.Element("spelling_bees")
        tree = ET.ElementTree(root)

    def fetch_puzzle(i):
        url = f"{BASE_URL}{i}"
        try:
            res = requests.get(url, timeout=5)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            date_span = soup.find("span", class_="bee-date")
            if not date_span:
                return None
            date_str = datetime.strptime(date_span.text.replace("Spelling Bee for", "").strip(), "%B %d, %Y").strftime("%Y-%m-%d")
            if date_str in existing_dates:
                return None

            words = [row.find("td", class_="bee-hover").get_text(strip=True).upper()
                     for row in soup.select("table.bee-set tr")
                     if row.find("td", class_="bee-hover")]
            return (date_str, url, words) if words else None
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_puzzle, i) for i in range(latest_id, start_id - 1, -1)]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Scraping"):
            result = future.result()
            if result:
                date_str, url, words = result
                prev_letters = get_previous_letters(date_str)
                new_letters = calculate_letters_attribute(words)
                if prev_letters and new_letters == prev_letters:
                    continue
                append_puzzle(root, date_str, url, words)

    root[:] = sorted(root, key=lambda p: p.attrib.get("date", ""))
    indent(root)
    tree.write(XML_FILE, encoding="utf-8", xml_declaration=True)
    print("✅ Scraping done.")

def get_previous_letters(latest_date):
    if not os.path.exists(XML_FILE):
        return None
    try:
        tree = ET.parse(XML_FILE)
        root = tree.getroot()
        all_puzzles = sorted(root.findall("puzzle"), key=lambda p: p.attrib.get("date", ""))
        prev = next((p for p in reversed(all_puzzles) if p.attrib.get("date") < latest_date), None)
        return prev.attrib.get("letters") if prev is not None else None
    except:
        return None

def fetch_from_nyt():
    today = date.today().strftime("%Y-%m-%d")
    existing_dates = load_existing_dates()
    if today in existing_dates:
        return
    print("🔍 Fetching NYT puzzle...")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(NYT_URL, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        script = next((s.string for s in soup.find_all("script") if s.string and "window.gameData" in s.string), None)
        json_str = script[script.find("{"): script.rfind("}") + 1]
        data = json.loads(json_str)
        words = [w.upper() for w in data.get("today", {}).get("answers", [])]
        new_letters = calculate_letters_attribute(words)
        prev_letters = get_previous_letters(today)
        if prev_letters and new_letters == prev_letters:
            print("⏩ NYT letters same as yesterday — skipping.")
            return
        if os.path.exists(XML_FILE):
            tree = ET.parse(XML_FILE)
            root = tree.getroot()
        else:
            root = ET.Element("spelling_bees")
            tree = ET.ElementTree(root)
        append_puzzle(root, today, NYT_URL, words)
        indent(root)
        tree.write(XML_FILE, encoding="utf-8", xml_declaration=True)
        print("✅ NYT puzzle added.")
    except:
        print("⚠️ NYT fetch failed.")

# ========== JUMBLER ========== #
def scramble_word(original):
    if len(original) <= 1:
        return original
    attempts = 0
    scrambled = original
    while scrambled == original and attempts < 10:
        chars = list(original)
        random.shuffle(chars)
        scrambled = ''.join(chars)
        attempts += 1
    return scrambled if scrambled != original else scrambled[::-1]

def copy_and_scramble_puzzles():
    def load_puzzles(path):
        if not os.path.exists(path):
            return None, []
        try:
            tree = ET.parse(path)
            return tree.getroot(), list(tree.getroot().findall("puzzle"))
        except:
            return None, []

    src_root, src_puzzles = load_puzzles(XML_FILE)
    if src_root is None:
        print("❌ bees.xml not found.")
        return

    if os.path.exists(TARGET_FILE):
        tgt_root, tgt_puzzles = load_puzzles(TARGET_FILE)
    else:
        tgt_root, tgt_puzzles = ET.Element("spelling_bees"), []

    tgt_tree = ET.ElementTree(tgt_root)
    existing_keys = {(p.attrib.get("date"), p.attrib.get("url")) for p in tgt_puzzles}
    src_map = {(p.attrib.get("date"), p.attrib.get("url")): p for p in src_puzzles}

    for p in src_puzzles:
        key = (p.attrib.get("date"), p.attrib.get("url"))
        if key not in existing_keys:
            tgt_root.append(p)

    for puzzle in tgt_root.findall("puzzle"):
        key = (puzzle.attrib.get("date"), puzzle.attrib.get("url"))
        src = src_map.get(key)
        if puzzle.attrib.get("jumbled") != "true":
            for i, word_el in enumerate(puzzle.findall("word")):
                original = src.findall("word")[i].text if src is not None else word_el.text
                scrambled = scramble_word(original)
                word_el.text = scrambled
                word_el.set("original_word", original)
            puzzle.attrib["jumbled"] = "true"

    tgt_root[:] = sorted(tgt_root, key=lambda p: p.attrib.get("date", ""))
    indent(tgt_root)
    tgt_tree.write(TARGET_FILE, encoding="utf-8", xml_declaration=True)
    print("🔀 jumbledbees.xml created.")

# ========== POSTER (FTP) ========== #
def upload_files():
    files = [INDEX_HTML, TARGET_FILE]
    try:
        with FTP() as ftp:
            ftp.connect(FTP_HOST, FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
            for filename in files:
                with open(filename, "rb") as f:
                    print(f"⬆️ Uploading {filename}...")
                    ftp.storbinary(f"STOR {filename}", f)
        print("✅ All files uploaded via FTP.")
    except Exception as e:
        print(f"❌ FTP upload failed: {e}")

# ========== RUN FULL PIPELINE ========== #
if __name__ == "__main__":
    scrape_sbsolver_month()
    fetch_from_nyt()
    copy_and_scramble_puzzles()
    upload_files()
