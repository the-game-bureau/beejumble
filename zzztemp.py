import os
from dotenv import load_dotenv
from substack import Api

# Load environment variables from .env file
load_dotenv()

# Initialize the Substack API client
api = Api(
    email=os.getenv("EMAIL"),
    password=os.getenv("PASSWORD"),
)

# Retrieve the User ID
user_id = api.get_user_id()
print(f"Your Substack User ID is: {user_id}")
