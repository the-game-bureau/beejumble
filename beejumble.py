import os
import requests
from bs4 import BeautifulSoup
import json
import xml.etree.ElementTree as ET
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from ftplib import FTP
import webbrowser

# FTP Server Details
FTP_HOST = "ftp.tii.ezv.temporary.site"
FTP_PORT = 21
FTP_USER = "beejumble@tii.ezv.temporary.site"
FTP_PASS = "{jTm-6zL$r_h"

# Define Central Time offset
CT_OFFSET = timedelta(hours=-6)
central_time_zone = timezone(CT_OFFSET)

# Generate date-specific filenames and display formats
current_date = datetime.now(central_time_zone)
formatted_date = current_date.strftime("%Y%m%d")
formatted_date_for_display = current_date.strftime("%A,%B%d,%Y")
xml_file_name = f"{formatted_date}BEEJUMBLE.xml"
html_file_name = f"{formatted_date}BEEJUMBLE.html"

# Set file paths to the current working directory
try:
    script_folder = Path(__file__).parent
except NameError:
    script_folder = Path('.')  # Use current directory if __file__ is unavailable

xml_file_path = script_folder / xml_file_name
html_file_path = script_folder / html_file_name
index_path = script_folder / "index.html"

# Function to scrape data from the NYT Spelling Bee puzzle page
def scrape_nyt_spelling_bee(xml_file_path):
    url = "https://www.nytimes.com/puzzles/spelling-bee"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        script_tag = soup.find("script", string=lambda x: "window.gameData" in x)
        if script_tag:
            json_data = json.loads(script_tag.string.split("= ", 1)[1].rstrip(";"))
            today_answers = json_data.get("today", {}).get("answers", [])
            if today_answers:
                root = ET.Element("root")
                for word in today_answers:
                    ET.SubElement(root, "word", length=str(len(word))).text = word
                ET.ElementTree(root).write(xml_file_path, encoding="utf-8", xml_declaration=True)
                print(f"Scraped and saved data to {xml_file_path}")
                return True
            else:
                print("No answers available in today's game data.")
    print("Failed to retrieve data.")
    return False

# Function to scramble words uniquely
def scramble_word(word, original_words, scrambled_set):
    word_list = list(word)
    scrambled = ''.join(word_list)
    while scrambled == word or scrambled in original_words or scrambled in scrambled_set:
        random.shuffle(word_list)
        scrambled = ''.join(word_list)
    scrambled_set.add(scrambled)
    return scrambled

# Parse and scramble XML data
def parse_scramble_and_sort_words(xml_file_path):
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        original_words = {word.text or "" for word in root.findall('.//word')}
        scrambled_set = set()
        scrambled_words = [
            (scramble_word(word.text or "", original_words, scrambled_set), word.get('length', '0'))
            for word in root.findall('.//word')
        ]
        scrambled_words.sort(key=lambda x: (len(x[0]), x[0]))
        words = [word for word, length in scrambled_words]
        lengths = [length for word, length in scrambled_words]
        return words, lengths
    except (FileNotFoundError, ET.ParseError):
        print(f"Error reading XML file: {xml_file_path}")
        return [], []

# Generate an HTML file from scrambled words
def generate_html(words, lengths, html_file_path):
    formatted_date_title = current_date.strftime("%m-%d-%a BeeJumble")
    formatted_date_header = current_date.strftime("%A, %B %d, %Y")

    with open(html_file_path, 'w') as html_file:
        html_file.write('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n')
        html_file.write('<meta name="viewport" content="width=device-width, initial-scale=1.0">\n')

        # Add CSS styles
        html_file.write('<style>')
        html_file.write('''
            @font-face { font-family: "FrankRuhl"; src: url("FrankRuhl.ttf") format("truetype"); }
            body { font-family: "FrankRuhl", sans-serif; font-size: 24px; }
            table { width: 100%; table-layout: fixed; }
            .beebutton {
                width: 50%;
                margin-top: 10px;
                padding: 15px 0;
                background-color: #FFD700;
                color: #333;
                font-size: 18px;
                border: 2px solid black;
                border-radius: 5px;
                cursor: pointer;
                text-align: center;
                font-weight: bold;
                text-decoration: none;
                font-family: "Interstate-Bold", sans-serif;
                display: inline-block;
            }
            .beebutton:hover { background-color: #FFC107; }
            .print-button-container { display: flex; justify-content: center; margin-bottom: 10px; }
            h4 { text-align: center; font-size: 20px; margin: 0; line-height: 1.2; }
            .title-spacer { margin-bottom: 20px; }
            @media print { .beebutton { display: none; } body { -webkit-print-color-adjust: exact; } }
            @page { size: letter landscape; margin: 10mm; }
            td { vertical-align: top; padding: 5px; }
            td > table { width: 100%; border-spacing: 0; }
            td > table td { border: none; }
            td > table td:nth-child(1) { font-size: 16px; text-align: center; white-space: nowrap; }
            td > table td:nth-child(2) { font-size: 24px; text-align: left; white-space: nowrap; }
        ''')
        html_file.write('</style>\n')

        html_file.write(f'<title>{formatted_date_title}</title>\n</head>\n<body>\n')

        # Print button
        html_file.write('<div class="print-button-container"><a href="javascript:window.print()" class="beebutton">Print</a></div>\n')
        html_file.write('<p></p>\n')

        html_file.write(f'<h4 style="text-align: center;">BeeJumble for {formatted_date_header}<br>'
                        'Brought to you by <a href="https://thegamebureau.com/beebox" target="_blank">thegamebureau.com</a></h4>\n')
        html_file.write('<div class="title-spacer"></div>\n<table>\n')

        max_columns = 3  # Three words per row
        words_per_row = (len(words) + max_columns - 1) // max_columns

        # Generate rows of words
        for i in range(words_per_row):
            html_file.write('<tr>\n')
            for j in range(max_columns):
                index = i * max_columns + j
                if index < len(words):
                    word = words[index]
                    length = lengths[index]
                    html_file.write('<td>\n<table>\n<tr>\n')
                    html_file.write(f'<td>{word}</td>\n')  # Scrambled word
                    html_file.write(f'<td>{"_ " * int(length)}</td>\n')  # Placeholder underscores
                    html_file.write('</tr>\n</table>\n</td>\n')
                else:
                    html_file.write('<td></td>\n')  # Empty cell
            html_file.write('</tr>\n')
        html_file.write('</table>\n</body>\n</html>')

    print(f"HTML file generated successfully as '{html_file_path}'")

# FTP upload function
def upload_file_to_ftp(local_file_path, remote_file_path):
    try:
        ftp = FTP()
        ftp.connect(FTP_HOST, FTP_PORT)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)
        print(f"Connected to FTP server: {FTP_HOST}")
        
        with open(local_file_path, 'rb') as file:
            ftp.storbinary(f"STOR {remote_file_path}", file)
        
        print(f"Uploaded {local_file_path} to {remote_file_path}")
        ftp.quit()
        return True
    except Exception as e:
        print(f"FTP upload failed: {e}")
        return False

# Run the data scraping, parsing, and HTML generation
if scrape_nyt_spelling_bee(xml_file_path):
    words, lengths = parse_scramble_and_sort_words(xml_file_path)
    if words:
        generate_html(words, lengths, html_file_path)
    else:
        print("Error: No words found in the XML file.")
else:
    print("Error: Failed to scrape data for XML file generation.")

# Add button to index.html if not already present
long_date = current_date.strftime("%A, %B %d, %Y")
new_button_html = f'''
<a href="https://tii.ezv.temporary.site/beejumble/archive/{html_file_name}" class="beebutton">{long_date}</a>
'''

if index_path.exists():
    with open(index_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    # Check if a button with the specific link already exists
    button_exists = soup.find("a", href=f"https://tii.ezv.temporary.site/beejumble/archive/{html_file_name}")
    
    if not button_exists:
        h3_tag = soup.find("h3")
        if h3_tag:
            h3_tag.insert_after(BeautifulSoup(new_button_html, "html.parser"))
        with open(index_path, "w", encoding="utf-8") as file:
            file.write(str(soup))
        print("Button added successfully to index.html")
    else:
        print("Button already exists in index.html")
else:
    print("index.html does not exist.")

# FTP Uploads
index_uploaded = upload_file_to_ftp(str(index_path), "index.html")  # Upload index.html to the root
html_uploaded = upload_file_to_ftp(str(html_file_path), f"archive/{html_file_name}")  # Upload HTML file to /archive

# If both files were uploaded successfully, delete temporary files
if index_uploaded and html_uploaded:
    for file in script_folder.glob("*JUMBLE.xml"):
        file.unlink()
    for file in script_folder.glob("*JUMBLE.html"):
        file.unlink()
    print("Temporary files deleted.")
else:
    print("Not all files were uploaded successfully. Temporary files retained.")


# URL to open
url = "https://tii.ezv.temporary.site/beejumble/"

# Open the URL in the default web browser
webbrowser.open(url)
