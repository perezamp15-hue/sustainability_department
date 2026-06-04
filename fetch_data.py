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
            print(f"Pulled {len(df_online)} rows from online source.")
    except Exception as e:
        print(f"SharePoint pull skipped: {e}")

    if os.path.exists("raw_data_inputs"):
        files = glob.glob("raw_data_inputs/*.xlsx") + glob.glob("raw_data_inputs/*.xls")
        for f in files:
            try:
                df_local = pd.read_excel(f, sheet_name=target_sheet, engine='openpyxl')
                all_dfs.append(df_local)
                print(f"Loaded {len(df_local)} rows from local file: {os.path.basename(f)}")
            except Exception as e:
                print(f"Skipped local file {f}: {e}")

    if not all_dfs:
        print("Error: No data sheets could be parsed.")
        return

    # Combine everything
    df = pd.concat(all_dfs, ignore_index=True)
    
    # Drop rows that are completely empty
    df.dropna(how='all', inplace=True)
    
    # CRITICAL: Clean up column names by shifting EVERYTHING to lowercase and stripping extra spaces
    df.columns = df.columns.str.strip().str.lower().str.replace(r'\s+', ' ', regex=True)
    print(f"Standardized columns found in file: {list(df.columns)}")

    # Define standard internal keys map (all lowercase to match our cleanup step)
    required_maps = {
        'service date': 'service_date',
        'site name': 'site_name',
        'address': 'address',
        'material': 'material',
        'material class': 'material_class',
        'weight (lbs)': 'weight',
        'cost': 'cost'
    }

    # Verify columns exist regardless of original capitalization or extra spacing
    for col in required_maps.keys():
        if col not in df.columns:
            # Fallback check: look for 'weight' or 'material class' if spelling varies slightly
            matching_cols = [c for c in df.columns if col in c or c in col]
            if matching_cols:
                df.rename(columns={matching_cols[0]: col}, inplace=True)
            else:
                raise KeyError(f"Missing column: '{col}'. Check your spreadsheet headers.")

    # Drop duplicate rows
    df.drop_duplicates(inplace=True)
    
    # Parse dates and fill missing values safely
    df['service_date'] = pd.to_datetime(df['service date'], errors='coerce')
    df = df.dropna(subset=['service_date'])
    
    df['weight'] = pd.to_numeric(df['weight (lbs)'], errors='coerce').fillna(0)
    df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0)
    
    df['address'] = df['address'].astype(str).str.strip().fillna('No Address')
    df['material'] = df['material'].astype(str).str.strip().fillna('Unknown Material')
    df['material_class'] = df['material class'].astype(str).str.strip().fillna('Unclassified')
    df['site_name'] = df['site name'].astype(str).str.strip().fillna('Unknown Site')
    
    # Generate dashboard tracking parameters
    df['MonthYear'] = df['service_date'].dt.to_period('M').astype(str)
    
    # Structure mapping output keys for index.html consumption
    raw_records = []
    for _, row in df.iterrows():
        raw_records.append({
            "MonthYear": str(row['MonthYear']),
            "Site Name": str(row['site_name']),
            "address": str(row['address']),
            "Material": str(row['material']),
            "Material Class": str(row['material_class']),
            "Weight (lbs)": float(row['weight']),
            "Cost": float(row['cost'])
        })
        
    # Isolate unique material classes for filter menus (excluding missing/blank options)
    material_classes = sorted(list(set([r['Material Class'] for r in raw_records if r['Material Class'] != 'nan' and r['Material Class'] != ''])))
    
    dashboard_payload = {
        "material_classes": material_classes,
        "records": raw_records
    }
    
    with open("dashboard_data.json", "w") as f:
        json.dump(dashboard_payload, f, indent=4)
        
    print(f"Data consolidation successful! Wrote {len(raw_records)} unique records to dashboard_data.json")

if __name__ == "__main__":
    run_pipeline()
