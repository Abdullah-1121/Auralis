import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from agents import function_tool
# Define the scope of API access
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Load credentials
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

# Create a client to interact with Google Sheets
client = gspread.authorize(creds)
for sheet in client.openall():
    print(sheet.title)
# Open your sheet
sheet = client.open("Auralis_ Leads_CRM").worksheet("Leads")  

# Function to save insights to Google Sheet
# @function_tool(name_override='Update_CRM')
def save_to_sheet(data: dict):
    sheet.append_row([
        data.get("Name", ""),
        data.get("Email", ""),
        data.get("Sentiment", ""),
        ", ".join(data.get("Pain_Points", [])),
        ", ".join(data.get("Intents", [])),
        ", ".join(data.get("Objections", [])),
        ", ".join(data.get("Risks", [])),
        ", ".join(data.get("Integrations", [])),
        data.get("Sales_Stage", ""),
        ", ".join(data.get("Next_Steps", [])),
        datetime.utcnow().isoformat()
    ])
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

save_to_sheet(insight_data)
