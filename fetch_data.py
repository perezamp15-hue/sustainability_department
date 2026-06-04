import pandas as pd
import requests
import json

# 1. Your SharePoint link modified with 'download=1' to force direct file streaming
sharepoint_url = "https://keckmedicine-my.sharepoint.com/:x:/g/personal/miguel_gonzalez_med_usc_edu/IQBOUo8yT_7MQ5MvTlv5MvcvAciCV_5EvAhQJMZTn1jqso4?download=1"

def run_pipeline():
    print("Fetching live data from SharePoint...")
    
    # 2. Download the file into memory using requests
    response = requests.get(sharepoint_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch file. Status code: {response.status_code}")
        
    # 3. Read Excel data using pandas
    # (openpyxl handles the modern Excel .xlsx format)
    df = pd.read_excel(response.content, engine='openpyxl')
    
    print(f"Successfully loaded file. Found {len(df)} rows.")

    # 4. DATA TRANSFORMATION PLACEHOLDER
    # Clean up or group your data here depending on your needs.
    # As an example, we will convert the whole dataframe into a clean JSON structure:
    transformed_data = df.to_dict(orient="records")
    
    # 5. Save the output directly as a file inside the repository
    with open("dashboard_data.json", "w") as f:
        json.dump(transformed_data, f, indent=4)
        
    print("Data processed and saved to dashboard_data.json")

if __name__ == "__main__":
    run_pipeline()
