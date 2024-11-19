import os
import requests
from bs4 import BeautifulSoup
import json
import xml.etree.ElementTree as ET
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
import ftplib
import webbrowser

# Define Central Time offset
CT_OFFSET = timedelta(hours=-6)
central_time_zone = timezone(CT_OFFSET)

# Generate date-specific filenames and display formats
current_date = datetime.now(central_time_zone)
formatted_date = current_date.strftime("%Y%m%d")
formatted_date_for_display = current_date.strftime("%A, %B %d, %Y")
xml_file_name = f"{formatted_date}BEEJUMBLE.xml"
html_file_name = f"{formatted_date}BEEJUMBLE.html"
beejumble_url = f"http://tii.ezv.temporary.site/beejumble/{html_file_name}"

# Set the directory to the same location as the .py file, with fallback to the current directory
try:
    script_folder = Path(__file__).parent
except NameError:
    script_folder = Path('.')
xml_file_path = script_folder / xml_file_name
html_file_path = script_folder / html_file_name

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
                    ET.SubElement(root, "word", length="_ " * len(word)).text = word
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
        html_file.write('<style>')
        html_file.write('@font-face { font-family: "FrankRuhl"; src: url("FrankRuhl.ttf") format("truetype"); }')
        html_file.write('body { font-family: "FrankRuhl", sans-serif; font-size: 24px; }')
        html_file.write('table { width: 100%; table-layout: fixed; }')
        html_file.write('.beebutton { width: 50%; margin-top: 10px; padding: 15px 0; background-color: #FFD700; color: #333;')
        html_file.write('font-size: 18px; border: 2px solid black; border-radius: 5px; cursor: pointer;')
        html_file.write('text-align: center; font-weight: bold; text-decoration: none; font-family: "Interstate-Bold", sans-serif;')
        html_file.write('display: inline-block; }')
        html_file.write('.beebutton:hover { background-color: #FFC107; }')
        html_file.write('.print-button-container { display: flex; justify-content: center; margin-bottom: 10px; }')
        html_file.write('h4 { text-align: center; font-size: 20px; margin: 0; line-height: 1.2; }')
        html_file.write('.title-spacer { margin-bottom: 20px; }')
        html_file.write('@media print { .beebutton { display: none; } body { -webkit-print-color-adjust: exact; } }')
        html_file.write('@page { size: letter landscape; margin: 10mm; }')
        html_file.write('</style>\n')
        html_file.write(f'<title>{formatted_date_title}</title>\n</head>\n<body>\n')

        # Print button with .beebutton class, centered with a <p> underneath
        html_file.write('<div class="print-button-container"><a href="javascript:window.print()" class="beebutton">Print</a></div>\n')
        html_file.write('<p></p>\n')  # Blank line for spacing

        html_file.write(f'<h4 style="text-align: center;">BeeJumble for {formatted_date_header}<br>'
                        'Brought to you by <a href="https://thegamebureau.com/beebox" target="_blank">thegamebureau.com</a></h4>\n')
        html_file.write('<div class="title-spacer"></div>\n<table>\n')

        max_columns = 8
        num_columns = min(max_columns, max(1, (len(words) + 14) // 15))
        words_per_column = (len(words) + num_columns - 1) // num_columns

        for i in range(words_per_column):
            html_file.write('<tr>\n')
            for j in range(num_columns):
                index = i + j * words_per_column
                if index < len(words):
                    html_file.write(
                        f'<td><table><tr>'
                        f'<td style="font-size: 16px; text-align: center; white-space: nowrap;">{words[index]}</td>'
                        f'<td style="font-size: 24px; text-align: left; white-space: nowrap;">{lengths[index]}</td>'
                        f'</tr></table></td>\n'
                    )
                else:
                    html_file.write('<td></td>\n')
            html_file.write('</tr>\n')
        html_file.write('</table>\n</body>\n</html>')

    print(f"HTML file generated successfully as '{html_file_path}'")

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
date_for_link = current_date.strftime("%Y%m%d")
new_button_html = f'''
<a href="http://tii.ezv.temporary.site/beejumble/{date_for_link}BEEJUMBLE.html" class="beebutton">{long_date}</a>
'''

index_path = script_folder / "index.html"
with open(index_path, "r", encoding="utf-8") as file:
    soup = BeautifulSoup(file, "html.parser")

button_exists = soup.find("a", href=f"http://tii.ezv.temporary.site/beejumble/{date_for_link}BEEJUMBLE.html")
if button_exists:
    print("Button for today's date already exists. No new button added.")
else:
    h3_tag = soup.find("h3", string="Bee Jumble is a twist on The New York Times Spelling Bee game. It takes the Spelling Bee words and jumbles them into a different game. It can also be used as hints for the Bee.")
    if h3_tag:
        h3_tag.insert_after(BeautifulSoup(new_button_html, "html.parser"))
    with open(index_path, "w", encoding="utf-8") as file:
        file.write(str(soup))
    print("Button added successfully to index.html")

# Upload all .html files to FTP
ftp_server = "ftp.tii.ezv.temporary.site"
ftp_username = "beejumble@tii.ezv.temporary.site"
ftp_password = "{jTm-6zL$r_h"
ftp_directory = ""

try:
    ftp = ftplib.FTP(ftp_server)
    ftp.login(user=ftp_username, passwd=ftp_password)
    ftp.cwd(ftp_directory)
    print(f"Connected to FTP server and changed to directory: {ftp_directory}")

    for file_name in os.listdir():
        if file_name.endswith('.html'):
            with open(file_name, 'rb') as file:
                ftp.storbinary(f'STOR {file_name}', file)
                print(f"Uploaded: {file_name}")

except ftplib.all_errors as e:
    print(f"FTP error: {e}. Continuing with the rest of the code.")
finally:
    try:
        ftp.quit()
    except:
        pass
    print("FTP connection closed.")

# Delete .html and .xml files except for index.html
for file_name in os.listdir():
    if (file_name.endswith('.html') or file_name.endswith('.xml')) and file_name != 'index.html':
        os.remove(file_name)
        print(f"Deleted: {file_name}")

print("Cleanup completed.")

# Open the main URL in the default browser
url = "tii.ezv.temporary.site/beejumble"
webbrowser.open(url)
