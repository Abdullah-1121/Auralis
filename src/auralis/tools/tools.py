import os
from typing import List
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from agents import function_tool
# Define the scope of API access
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
current_dir = os.path.dirname(__file__)
creds_path = os.path.join(current_dir, "credentials.json")
# Load credentials
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)

# Create a client to interact with Google Sheets
client = gspread.authorize(creds)
for sheet in client.openall():
    print(sheet.title)
# Open your sheet
sheet = client.open("Auralis_ Leads_CRM").worksheet("Leads")  

# Function to save insights to Google Sheet
@function_tool(name_override='Update_CRM')
def save_to_sheet(
    name: str = "",
    email: str = "",
    sentiment: str = "",
    pain_points: List[str] = [],
    intents: List[str] = [],
    objections: List[str] = [],
    risks: List[str] = [],
    integrations: List[str] = [],
    sales_stage: str = "",
    next_steps: List[str] = []
):
    # Append to the Google Sheet
    try:
     sheet.append_row([
        name,
        email,
        sentiment,
        ", ".join(pain_points),
        ", ".join(intents),
        ", ".join(objections),
        ", ".join(risks),
        ", ".join(integrations),
        sales_stage,
        ", ".join(next_steps),
        datetime.utcnow().isoformat()
    ])
     print("Data saved to Google Sheet successfully!")
    except Exception as e:
        print(f"Error saving to Google Sheet: {e}")
        
insight_data = {
    "Name": "Jordan",
    "Email": "jordan@onyxlearning.com",
    "Sentiment": "positive",
    "Pain_Points": ["Instructor onboarding", "Contractor reliance"],
    "Intents": ["Centralize platform", "Reduce overhead"],
    "Objections": [],
    "Risks": ["Contractor bottleneck"],
    "Integrations": ["Canvas LMS", "Slack"],
    "Sales_Stage": "Technical evaluation",
    "Next_Steps": ["Schedule deep dive", "Share pricing"]
}

# save_to_sheet(insight_data)
