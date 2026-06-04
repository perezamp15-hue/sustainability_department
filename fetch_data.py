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

    df = pd.concat(all_dfs, ignore_index=True)
    df.dropna(how='all', inplace=True)
    
    # 1. Clean the headers into standardized lowercase strings
    df.columns = df.columns.str.strip().str.lower().str.replace(r'\s+', ' ', regex=True)
    print(f"Standardized columns found in file: {list(df.columns)}")

    # 2. Check and align expected raw keys to unified internal standard keys
    # Raw file columns look like: 'service date', 'site name', 'material class', 'weight (lbs)'
    required_maps = {
        'service date': 'service_date',
        'site name': 'site_name',
        'material class': 'material_class',
        'weight (lbs)': 'weight'
    }

    for target_raw, internal_name in required_maps.items():
        if target_raw in df.columns:
            df.rename(columns={target_raw: internal_name}, inplace=True)
        else:
            # Fallback search strategy if spaces vary slightly
            matching_cols = [c for c in df.columns if target_raw in c or c in target_raw]
            if matching_cols:
                df.rename(columns={matching_cols[0]: internal_name}, inplace=True)
            else:
                raise KeyError(f"Critical Column Missing! Looking for: '{target_raw}'. Columns found: {list(df.columns)}")

    df.drop_duplicates(inplace=True)
    
    # 3. Clean and parse variables
    df['service_date'] = pd.to_datetime(df['service_date'], errors='coerce')
    df = df.dropna(subset=['service_date'])
    df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0)
    
    df['material_class'] = df['material_class'].astype(str).str.strip().fillna('Unclassified')
    df['site_name'] = df['site_name'].astype(str).str.strip().fillna('Unknown Site')
    
    # Extract structural time grouping definitions
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
        
    # Compile distinct options for layout filter blocks
    material_classes = sorted(list(set([r['Material Class'] for r in raw_records if r['Material Class'] not in ['nan', '']])))
    site_locations = sorted(list(set([r['Site Name'] for r in raw_records if r['Site Name'] not in ['nan', '']])))
    
    dashboard_payload = {
        "material_classes": material_classes,
        "site_locations": site_locations,
        "records": raw_records
    }
    
    with open("dashboard_data.json", "w") as f:
        json.dump(dashboard_payload, f, indent=4)
        
    print(f"Data package ready! Packed {len(raw_records)} clean records for the custom dashboard layout.")

if __name__ == "__main__":
    run_pipeline()
