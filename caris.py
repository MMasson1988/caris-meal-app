import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_google_sheet(sheet_id, worksheet_name='mastersheet', credentials_file='credentials.json'):
    """
    Loads a Google Sheet into a Pandas DataFrame.

    Args:
        sheet_id (str): The Google Sheets document ID.
        worksheet_name (str, optional): The name of the worksheet to retrieve. Defaults to 'Hello world'.
        credentials_file (str, optional): Path to the Google service account JSON credentials file. Defaults to 'credentials.json'.

    Returns:
        pd.DataFrame: The loaded data as a Pandas DataFrame.
    """
    try:
        # Set up Google Sheets API
        scopes = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        client = gspread.authorize(creds)
        
        workbrook = client.open_by_key(sheet_id)
        sheet = workbrook.worksheet(worksheet_name)

        # Get all records
        records = sheet.get_all_records()
        df = pd.DataFrame(records)

        return df

    except Exception as e:
        print(f"Error loading Google Sheet: {e}")
        return None

# Example usage
#sheet_id = '1ZQD6jePvbffO0JT-j1c4BEDizB7WjBII8avuS7t5ELw'
#df = load_google_sheet(sheet_id)
# Compare this snippet from maintest.py:
# import gspread
# from google.oauth2.service_account import Credentials
# import pandas as pd
#