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