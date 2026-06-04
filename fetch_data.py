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
    
    # Standardize spaces and lower strings to match indices cleanly
    df.columns = df.columns.str.strip().str.lower().str.replace(r'\s+', ' ', regex=True)

    required_maps = {
        'service date': 'service_date',
        'site name': 'site_name',
        'material class': 'material_class',
        'weight (lbs)': 'weight'
    }

    for col in required_maps.keys():
        if col not in df.columns:
            matching_cols = [c for c in df.columns if col in c or c in col]
            if matching_cols:
                df.rename(columns={matching_cols[0]: col}, inplace=True)
            else:
                raise KeyError(f"Missing required column: '{col}'")

    df.drop_duplicates(inplace=True)
    
    # Cast fields
    df['service_date'] = pd.to_datetime(df['service date'], errors='coerce')
    df = df.dropna(subset=['service_date'])
    df['weight'] = pd.to_numeric(df['weight (lbs)'], errors='coerce').fillna(0)
    
    df['material_class'] = df['material_class'].astype(str).str.strip().fillna('Unclassified')
    df['site_name'] = df['site_name'].astype(str).str.strip().fillna('Unknown Site')
    
    # Separate explicit chronological metrics
    df['MonthYear'] = df['service_date'].dt.to_period('M').astype(str)
    df['Year'] = df['service_date'].dt.year.astype(str)
    
    # Map array structure values
    raw_records = []
    for _, row in df.iterrows():
        raw_records.append({
            "Year": str(row['Year']),
            "MonthYear": str(row['MonthYear']),
            "Site Name": str(row['site_name']),
            "Material Class": str(row['material_class']),
            "Weight (lbs)": float(row['weight'])
        })
        
    # Compile distinct structural sorting keys
    material_classes = sorted(list(set([r['Material Class'] for r in raw_records if r['Material Class'] not in ['nan', '']])))
    site_locations = sorted(list(set([r['Site Name'] for r in raw_records if r['Site Name'] not in ['nan', '']])))
    
    dashboard_payload = {
        "material_classes": material_classes,
        "site_locations": site_locations,
        "records": raw_records
    }
    
    with open("dashboard_data.json", "w") as f:
        json.dump(dashboard_payload, f, indent=4)
        
    print(f"Data package ready! Packed {len(raw_records)} clean records for layout charts.")

if __name__ == "__main__":
    run_pipeline()
