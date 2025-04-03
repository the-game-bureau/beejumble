# -------------------------------------------------------------------
# 🌀 BEEJUMBLE JUMBLER
#
# This script creates a jumbled version of bees.xml called jumbledbees.xml.
# It performs two main tasks:
#
# 1. COPY + UPDATE:
#    - Loads all puzzles from bees.xml.
#    - Adds any missing puzzles to jumbledbees.xml.
#
# 2. SCRAMBLE:
#    - For any puzzle not already marked as "jumbled", it scrambles the letters
#      of each word (leaving very short words unchanged).
#    - Ensures the scrambled word is not identical to the original.
#    - Sets a `jumbled="true"` attribute on each processed puzzle.
#
# All puzzles are sorted by date and saved in a compact, readable XML format.
#
# Output: jumbledbees.xml (ready for print/play or game display)
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

    # Step 2: Scramble unjumbled puzzles
    scrambled_count = 0
    for puzzle in target_root.findall("puzzle"):
        if puzzle.attrib.get("jumbled") == "true":
            continue

        for word_el in puzzle.findall("word"):
            original = word_el.text or ""
            scrambled = scramble_word(original)
            word_el.text = scrambled

        sort_words_in_puzzle(puzzle)
        puzzle.attrib["jumbled"] = "true"
        scrambled_count += 1

    if scrambled_count > 0:
        print(f"🔀 Jumbled {scrambled_count} puzzle(s).")
    else:
        print("✨ All puzzles already jumbled.")

    target_root[:] = sorted(target_root, key=lambda p: p.attrib.get("date", ""))
    indent(target_root)
    target_tree.write(TARGET_FILE, encoding="utf-8", xml_declaration=True)
    print(f"📦 {TARGET_FILE} saved and formatted.")

if __name__ == "__main__":
    copy_and_scramble_puzzles()