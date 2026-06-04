import pandas as pd
import json
import os
import glob
import requests
import io

sharepoint_url = "https://keckmedicine-my.sharepoint.com/personal/miguel_gonzalez_med_usc_edu/_layouts/15/download.aspx?SourceUrl=https://keckmedicine-my.sharepoint.com/personal/miguel_gonzalez_med_usc_edu/:x:/g/personal/miguel_gonzalez_med_usc_edu/IQBOUo8yT_7MQ5MvTlv5MvcvAciCV_5EvAhQJMZTn1jqso4"

def run_pipeline():
    all_dfs = []
    target_sheet = "RawData" 
    
    print("Pulling live data from SharePoint...")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(sharepoint_url, headers=headers)
        if res.status_code == 200:
            df_online = pd.read_excel(io.BytesIO(res.content), sheet_name=target_sheet, engine='openpyxl')
            all_dfs.append(df_online)
    except Exception as e:
        print(f"URL pull skipped: {e}")

    if os.path.exists("raw_data_inputs"):
        files = glob.glob("raw_data_inputs/*.xlsx") + glob.glob("raw_data_inputs/*.xls")
        for f in files:
            try:
                df_local = pd.read_excel(f, sheet_name=target_sheet, engine='openpyxl')
                all_dfs.append(df_local)
            except Exception as e:
                print(f"Skipped local file {f}: {e}")

    if not all_dfs:
        print("Error: No data found.")
        return

    df = pd.concat(all_dfs, ignore_index=True)
    df.dropna(how='all', inplace=True)
    df.columns = df.columns.str.strip()
    
    # Check that our exact Excel columns exist
    required_cols = ['Service Date', 'Site Name', 'Weight (lbs)', 'Cost', 'Material Class']
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Missing column: '{col}'. Ensure it matches your Excel headers.")

    df.drop_duplicates(inplace=True)
    
    # Data Formatting
    df['Service Date'] = pd.to_datetime(df['Service Date'], errors='coerce')
    df = df.dropna(subset=['Service Date'])
    df['Weight (lbs)'] = pd.to_numeric(df['Weight (lbs)'], errors='coerce').fillna(0)
    df['Cost'] = pd.to_numeric(df['Cost'], errors='coerce').fillna(0)
    df['Material Class'] = df['Material Class'].astype(str).str.strip().fillna('Unclassified')
    df['MonthYear'] = df['Service Date'].dt.to_period('M').astype(str)
    
    # Output the raw cleaned records so the JavaScript dashboard can handle dynamic filtering
    raw_records = df[['MonthYear', 'Site Name', 'Material Class', 'Weight (lbs)', 'Cost']].to_dict(orient='records')
    
    # Get a distinct list of waste material types to generate our dashboard filter options
    material_types = sorted(list(df['Material Class'].unique()))
    
    dashboard_payload = {
        "material_types": material_types,
        "records": raw_records
    }
    
    with open("dashboard_data.json", "w") as f:
        json.dump(dashboard_payload, f, indent=4)
        
    print(f"Successfully processed {len(raw_records)} rows for dynamic filtering.")

if __name__ == "__main__":
    run_pipeline()
