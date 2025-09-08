import requests
import json
import pandas as pd
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
# Get system timezone
import time
import re
load_dotenv()

def get_commcare_odata(url, auth_credentials, filter_params):
    """
    Fetch active muso groups from CommCare using OData API
    
    Args:
        url (str): The OData API URL
        auth_credentials (tuple): Username and password tuple (username, password)
        filter_params (dict): Parameters to filter the data
        
    Returns:
        list: List of muso group records
    """
    # Make the initial request to the OData API
    response = requests.get(url, auth=auth_credentials, params=filter_params)

    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: API request failed with status code {response.status_code}")
        return []
    # Get initial data
    data = response.json()['value']
    # Follow pagination links if they exist
    while "@odata.nextLink" in response.json():
        next_link = response.json()["@odata.nextLink"]
        print(f"Following next link: {next_link}")
        
        # Get the next page of data
        response = requests.get(next_link, auth=auth_credentials)
        
        if response.status_code == 200:
            # Add new records to our data
            new_records = response.json()['value']
            data += new_records
            print(f"Retrieved additional {len(new_records)} records. Total: {len(data)}")
        else:
            print(f"Error: Failed to retrieve next page: {response.status_code}")
            break
    
    print(f"Total records retrieved: {len(data)}")
    return data



def is_beneficiary_active(row):
    """
    Check if a beneficiary is active based on various date fields
    Args:
        row (dict): A dictionary representing a beneficiary record
        start_date (str): The start date for the active period
        end_date (str): The end date for the active period"
        """
    if row['closed_date']<start_date:
        return "no"
    if row["creation_date"]>end_date:
        return "no"
    if row['graduation_date']>start_date:
        return "yes"
    if row['abandoned_date']>start_date:
        return "yes"
    if row['inactive_date']>start_date:
        return "yes"
    if row['inactive_date']<start_date:
        return "no"
    if row['graduation_date']<start_date:
        return "no"
    if (pd.isnull(row['is_inactive']) or row['is_inactive']==0) and (row['graduated']==0 or pd.isnull(row['graduated'])):
        return "yes"
    return "no"


# define a function to check if a group is active
def is_groupe_active(row):
    """
    Check if a group is active based on various date fields
    Args:
        row (dict): A dictionary representing a group record
    Returns:
        str: 'yes' if active, 'no' if inactive
    """
        # Convert reference dates to UTC timezone-aware timestamps
    start_date_dt = pd.to_datetime(start_date)
    end_date_dt = pd.to_datetime(end_date)
    print("start date and end date", start_date_dt, end_date_dt)
    
    # Convert and normalize dates from the row
    # Check conditions only if dates are valid
    if row["office_name"] in ["CAY","JER"]:
        return "no"
    # if pd.notna(row['opened_date']) and row['opened_date'] < start_date_dt:
    #     return "no"
    if pd.notna(row['closed_date']) and row['closed_date'] < start_date_dt:
        return "no"
    if pd.notna(row['creation_date']) and row["creation_date"] > end_date_dt:
        return "no"
    if pd.notna(row['graduation_date']) and row['graduation_date'] > start_date_dt:
        return "yes"
    if pd.notna(row['inactive_date']) and row['inactive_date'] > start_date_dt:
        return "yes"
    if pd.notna(row['inactive_date']) and row['inactive_date'] < start_date_dt:
        return "no"
    if pd.notna(row['graduation_date']) and row['graduation_date'] < start_date_dt:
        return "no"
    if (pd.isnull(row['is_inactive']) or row['is_inactive']==0) and (row['is_graduated']==0 or pd.isnull(row['is_graduated'])):
        return "yes"
    return "no"

import re
from datetime import datetime
import os

def file_matches_today(base, fname):
    today = datetime.today().strftime('%Y-%m-%d')
    base_norm = base.lower().replace(" ", "_")
    fname_norm = os.path.basename(fname).lower().replace(" ", "_")
    pat = re.compile(rf"^{re.escape(base_norm)}\s+{today}(?:\s+\(\d+\))?\.xlsx$")
    return bool(pat.match(fname_norm))
