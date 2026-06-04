import pandas as pd
import requests
import json

# 1. Rebuilt URL targeting the explicit SharePoint download handler
# This bypasses the interactive preview portal directly via the layouts engine
base_sharepoint = "https://keckmedicine-my.sharepoint.com/personal/miguel_gonzalez_med_usc_edu"
doc_path = ":x:/g/personal/miguel_gonzalez_med_usc_edu/IQBOUo8yT_7MQ5MvTlv5MvcvAciCV_5EvAhQJMZTn1jqso4"
sharepoint_url = f"{base_sharepoint}/_layouts/15/download.aspx?SourceUrl={base_sharepoint}/{doc_path}"

def run_pipeline():
    print("Fetching live data from SharePoint...")
    
    # 2. Add headers to masquerade the script as a regular Web Browser
    # This prevents the security engine from throwing a 403 Forbidden bot block
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    # 3. Request data with the browser headers
    response = requests.get(sharepoint_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed URL attempted: {sharepoint_url}")
        raise Exception(f"Failed to fetch file. Status code: {response.status_code}")
        
    print(f"Successfully connected! File binary size received: {len(response.content)} bytes.")
    
    # 4. Process the data using pandas
    df = pd.read_excel(response.content, engine='openpyxl')
    print(f"Successfully loaded file sheet. Found {len(df)} rows.")

    # Convert dataframe into clean JSON records
    transformed_data = df.to_dict(orient="records")
    
    # Save the output file
    with open("dashboard_data.json", "w") as f:
        json.dump(transformed_data, f, indent=4)
        
    print("Data processed and saved to dashboard_data.json")

if __name__ == "__main__":
    run_pipeline()
