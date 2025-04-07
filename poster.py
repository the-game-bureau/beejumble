# -------------------------------------------------------------------
# 📡 BEE JUMBLE POSTER
#
# This script uploads Bee Jumble game files to a remote FTP server.
# It is typically run after generating `jumbledbees.xml` and any
# related display files like `index.htm`.
#
# Key responsibilities:
# -------------------------------------------------------------------
# ✅ Connects to the FTP server using provided credentials.
# ✅ Uploads specified files (binary mode) to the server root.
# ✅ Displays a progress message for each file.
# ✅ Confirms success after all uploads are complete.
#
# Configuration:
# - FTP credentials are defined at the top of the script.
# - File list (`files_to_upload`) can be customized as needed.
#
# Usage:
#   python post.py
#
# Output:
#   - Files uploaded to: ftp://tii.ezv.temporary.site
#
# Dependencies:
#   - Python standard library only (no external packages required).
#
# Suggested Workflow:
#   1. Run `go.py` to generate fresh XML and HTML.
#   2. Run this script to publish your Bee Jumble updates.
# -------------------------------------------------------------------
from ftplib import FTP

# FTP server credentials
FTP_HOST = "ftp.tii.ezv.temporary.site"
FTP_PORT = 21
FTP_USER = "beejumble@tii.ezv.temporary.site"
FTP_PASS = "{jTm-6zL$r_h"

# Files to upload
files_to_upload = ["index.htm", "jumbledbees.xml"]

# Connect and upload
with FTP() as ftp:
    ftp.connect(FTP_HOST, FTP_PORT)
    ftp.login(FTP_USER, FTP_PASS)

    for filename in files_to_upload:
        with open(filename, "rb") as f:
            print(f"Uploading {filename}...")
            ftp.storbinary(f"STOR {filename}", f)

    print("✅ All files uploaded successfully.")