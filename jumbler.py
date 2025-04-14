# -------------------------------------------------------------------
# 🐝 BEE JUMBLE JUMBLER
#
# This script generates a new XML file (`jumbledbees.xml`) from the
# source puzzle archive (`bees.xml`) for use in printable games,
# online display, or testing.
#
# It performs two main tasks:
#
# 1. COPY + UPDATE:
#    - Loads all puzzles from `bees.xml`.
#    - Copies over any puzzles that are missing from `jumbledbees.xml`.
#    - Matches puzzles based on a composite key of (date, url).
#
# 2. SCRAMBLE:
#    - For any puzzle that is not already marked `jumbled="true"`:
#      - Scrambles each word (shuffled randomly but avoids unchanged results).
#      - Preserves the original word in a new `original_word` attribute.
#      - Marks the puzzle as `jumbled="true"`.
#    - For already-jumbled puzzles:
#      - Ensures every word has a correct `original_word` attribute.
#
# Additional logic:
# - Words are sorted by length, then alphabetically, for consistency.
# - All puzzles are re-sorted by date after updates.
# - Final output is indented for compact, readable XML formatting.
#
# Output:
#   📄 jumbledbees.xml (auto-created or updated)
#
# Typical Use Cases:
#   - Prepare puzzles for printing or visual play without revealing answers.
#   - Ensure jumbled puzzles are synced with the source puzzle set.
#   - Safely patch older puzzles that lack `original_word` data.
#
# Notes:
# - Scrambling is deterministic per run but not reproducible across runs.
# - If scrambling fails to change a word after 10 tries, it reverses the word.
#
# Usage:
#   python jumbler.py
#
# Dependencies:
#   - Python standard library only (no external packages required).
# -------------------------------------------------------------------

import os
import xml.etree.ElementTree as ET
import random

SOURCE_FILE = "bees.xml"
TARGET_FILE = "jumbledbees.xml"

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
        if not elem.text or not elem.text.strip():
            elem.text = ''
        if not elem.tail or not elem.tail.strip():
            elem.tail = i

def load_puzzles(xml_path):
    if not os.path.exists(xml_path):
        return None, []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        puzzles = list(root.findall("puzzle"))
        return root, puzzles
    except ET.ParseError:
        print(f"⚠️ Could not parse {xml_path}.")
        return None, []

def get_puzzle_key(p):
    return (p.attrib.get("date"), p.attrib.get("url"))

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
    if scrambled == original:
        if len(scrambled) > 1:
            scrambled = scrambled[::-1]
    return scrambled

def sort_words_in_puzzle(puzzle):
    words = puzzle.findall("word")
    sorted_words = sorted(words, key=lambda w: (int(w.attrib.get("length", 0)), w.text.lower() if w.text else ""))
    for word in words:
        puzzle.remove(word)
    for word in sorted_words:
        puzzle.append(word)

def copy_and_scramble_puzzles():
    source_root, source_puzzles = load_puzzles(SOURCE_FILE)
    if source_root is None:
        print(f"❌ Source file {SOURCE_FILE} is missing or unreadable.")
        return

    if os.path.exists(TARGET_FILE):
        target_root, target_puzzles = load_puzzles(TARGET_FILE)
        if target_root is None:
            print(f"⚠️ Target file {TARGET_FILE} was unreadable. Starting fresh.")
            target_root = ET.Element("spelling_bees")
            target_tree = ET.ElementTree(target_root)
            target_puzzles = []
        else:
            target_tree = ET.ElementTree(target_root)
    else:
        target_root = ET.Element("spelling_bees")
        target_tree = ET.ElementTree(target_root)
        target_puzzles = []

    existing_keys = {get_puzzle_key(p): p for p in target_puzzles}
    source_map = {get_puzzle_key(p): p for p in source_puzzles}
    added = 0

    # Step 1: Add missing puzzles
    for p in source_puzzles:
        key = get_puzzle_key(p)
        if key not in existing_keys:
            target_root.append(p)
            added += 1

    if added > 0:
        print(f"🧩 Added {added} missing puzzle(s) to {TARGET_FILE}.")
    else:
        print("✅ No missing puzzles found.")

    # Step 2: Scramble or patch original_word from source
    scrambled_count = 0
    patched_originals = 0

    for puzzle in target_root.findall("puzzle"):
        key = get_puzzle_key(puzzle)
        source_puzzle = source_map.get(key)
        original_words = [w.text for w in source_puzzle.findall("word")] if source_puzzle is not None else []

        if puzzle.attrib.get("jumbled") != "true":
            # Jumble + add original_word from source
            for idx, word_el in enumerate(puzzle.findall("word")):
                original = original_words[idx] if idx < len(original_words) else (word_el.text or "")
                scrambled = scramble_word(original)
                word_el.text = scrambled
                word_el.set("original_word", original)
            sort_words_in_puzzle(puzzle)
            puzzle.attrib["jumbled"] = "true"
            scrambled_count += 1
        else:
            # Already jumbled — just ensure original_word is patched from bees.xml
            for idx, word_el in enumerate(puzzle.findall("word")):
                if "original_word" not in word_el.attrib:
                    original = original_words[idx] if idx < len(original_words) else (word_el.text or "")
                    word_el.set("original_word", original)
                    patched_originals += 1

    if scrambled_count > 0:
        print(f"🔀 Jumbled {scrambled_count} puzzle(s).")
    else:
        print("✨ All puzzles already jumbled.")

    if patched_originals > 0:
        print(f"🛠️ Patched {patched_originals} word(s) with original_word from source.")

    # Step 3: Save
    target_root[:] = sorted(target_root, key=lambda p: p.attrib.get("date", ""))

        # Step 3b: Mark most recent puzzle with subscribersonly="yes"
    if target_root:
        latest_puzzle = max(target_root, key=lambda p: p.attrib.get("date", ""))
        for puzzle in target_root:
            if puzzle is latest_puzzle:
                puzzle.set("subscribersonly", "no")
            else:
                puzzle.attrib.pop("subscribersonly", None)

    indent(target_root)
    target_tree.write(TARGET_FILE, encoding="utf-8", xml_declaration=True)
    print(f"📦 {TARGET_FILE} saved and formatted.")

if __name__ == "__main__":
    copy_and_scramble_puzzles()
