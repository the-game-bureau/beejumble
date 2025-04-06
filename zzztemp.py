import xml.etree.ElementTree as ET
from uuid import uuid4

# Load the XML file
tree = ET.parse('bees.xml')
root = tree.getroot()

# Track used IDs to ensure uniqueness (extra safety, though UUIDs are already unique)
used_ids = set()

# Assign a unique puzzleid to each puzzle element
for puzzle in root.findall('puzzle'):
    new_id = str(uuid4())
    while new_id in used_ids:
        new_id = str(uuid4())
    used_ids.add(new_id)
    puzzle.set("puzzleid", new_id)

# Save the updated XML to a new file
tree.write('bees_with_ids.xml', encoding='utf-8', xml_declaration=True)

print("puzzleid attributes added and saved to bees_with_ids.xml")
