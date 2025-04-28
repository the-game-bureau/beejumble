#!/usr/bin/env python3
"""
📅 New Spelling Bee Harvester – harvest.py

Fetches Spelling Bee puzzles from the last 10 days (including today) 
based on https://www.nytimes.com/puzzles/spelling-bee/YYYY-MM-DD,
adds them to bees.xml if missing, sorted chronologically (newest at bottom).
"""

import os
import time
import json
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ─── Configuration ─────────────────────────────────────────────────────────────
XML_FILE = "bees.xml"  # Save directly to bees.xml in the project root
BASE_URL = "https://www.nytimes.com/puzzles/spelling-bee"

# ─── Pretty-Print XML ──────────────────────────────────────────────────────────
def indent(elem, level=0):
    i = "\n" + "  " * level
    j = "\n" + "  " * (level + 1)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = j
        for idx, child in enumerate(elem):
            indent(child, level + 1)
            child.tail = j if idx < len(elem) - 1 else i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

# ─── Load existing bees.xml ────────────────────────────────────────────────────
if os.path.exists(XML_FILE):
    tree = ET.parse(XML_FILE)
    root = tree.getroot()
else:
    root = ET.Element("puzzles")
    tree = ET.ElementTree(root)

# ─── Get list of already existing puzzle dates ──────────────────────────────────
existing_dates = {puzzle.get("date") for puzzle in root.findall("puzzle")}

# ─── Fetch and add new puzzles ──────────────────────────────────────────────────
today = datetime.now()

for days_ago in range(0, 10):  # 0 to 9 days ago (including today)
    date_obj = today - timedelta(days=days_ago)
    date_str = date_obj.strftime("%Y-%m-%d")

    if date_str in existing_dates:
        print(f"✅ {date_str} already exists, skipping.")
        continue

    url = f"{BASE_URL}/{date_str}"
    print(f"🔎 Fetching {url} ...")

    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if response.status_code != 200:
            print(f"⚠️  Skipped {date_str} (status {response.status_code})")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        # Find <script> containing window.gameData
        script_tag = next(
            (s.string for s in soup.find_all("script") if s.string and "window.gameData" in s.string),
            None
        )
        if not script_tag:
            print(f"⚠️  No gameData found for {date_str}")
            continue

        # Extract JSON manually
        start = script_tag.find("{")
        brace_count = 0
        for i in range(start, len(script_tag)):
            if script_tag[i] == '{':
                brace_count += 1
            elif script_tag[i] == '}':
                brace_count -= 1
            if brace_count == 0:
                json_str = script_tag[start:i + 1]
                break

        data = json.loads(json_str)
        puzzle_data = data.get("today", {})

        answers = puzzle_data.get("answers", [])
        center_letter = puzzle_data.get("centerLetter", "").upper()
        outer_letters = [l.upper() for l in puzzle_data.get("outerLetters", [])]
        full_letters = center_letter + ''.join(outer_letters)
        puzzle_id = str(puzzle_data.get("id", ""))  # 🛠️ Force to string

        if not answers or not center_letter or not outer_letters:
            print(f"⚠️  Missing puzzle data for {date_str}")
            continue

        # Build the <puzzle> element
        puzzle_elem = ET.Element(
            "puzzle",
            date=date_str,
            url="https://www.nytimes.com/puzzles/spelling-bee",
            puzzleid=puzzle_id,
            letters=full_letters
        )

        # FIRST, add all <word length="X"> elements
        sorted_answers = sorted(a.upper() for a in answers)
        for word in sorted_answers:
            word_elem = ET.SubElement(puzzle_elem, "word", length=str(len(word)))
            word_elem.text = word

        # THEN, add <letter1> to <letter7> elements
        letter_counts = {letter: 0 for letter in full_letters}
        for word in sorted_answers:
            first_letter = word[0]
            if first_letter in letter_counts:
                letter_counts[first_letter] += 1

        for idx, letter in enumerate(full_letters):
            count = letter_counts.get(letter, 0)
            letter_elem = ET.SubElement(puzzle_elem, f"letter{idx+1}")
            letter_elem.text = str(count)

        root.append(puzzle_elem)
        print(f"📝 Added puzzle for {date_str} with {len(answers)} words.")

        time.sleep(1)  # polite delay

    except Exception as e:
        print(f"❌ Error fetching {date_str}: {e}")

# ─── Save updated bees.xml ─────────────────────────────────────────────────────
indent(root)
tree.write(XML_FILE, encoding="utf-8", xml_declaration=True)
print(f"\n✅ Finished updating {XML_FILE}")
