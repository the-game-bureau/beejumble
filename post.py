import os
import requests
from dotenv import load_dotenv
from datetime import datetime
import platform
import xml.etree.ElementTree as ET

# Load environment variables from substack.env
load_dotenv("substack.env")
SID = os.getenv("SUBSTACK_SID")
DOMAIN = "beebox.substack.com"

def get_latest_puzzle(xml_path="jumbledbees.xml"):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        latest = {"puzzleid": None, "date": None}
        for puzzle in root.findall("puzzle"):
            date_str = puzzle.attrib.get("date")
            pid = puzzle.attrib.get("puzzleid")
            if date_str and pid:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    if latest["date"] is None or date_obj > latest["date"]:
                        latest["date"] = date_obj
                        latest["puzzleid"] = pid
                except ValueError:
                    continue
        if latest["puzzleid"] and latest["date"]:
            return latest["puzzleid"], latest["date"]
    except Exception as e:
        print(f"⚠️ XML error: {e}")
    return "unknown", None

def format_friendly_date(date_obj):
    if not date_obj:
        return "Today"
    fmt = "%B %-d, %Y" if platform.system() != "Windows" else "%B %#d, %Y"
    return date_obj.strftime(fmt)

def create_draft_post():
    puzzle_id, puzzle_date = get_latest_puzzle()
    formatted_date = format_friendly_date(puzzle_date)
    puzzle_link = f"https://tii.ezv.temporary.site/beejumble?puzzleid={puzzle_id}"
