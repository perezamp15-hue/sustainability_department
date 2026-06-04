import pandas as pd
import json
import os
import glob
import requests
import io

# Explicit direct download link formatting
sharepoint_url = "https://keckmedicine-my.sharepoint.com/personal/miguel_gonzalez_med_usc_edu/_layouts/15/download.aspx?SourceUrl=https://keckmedicine-my.sharepoint.com/personal/miguel_gonzalez_med_usc_edu/:x:/g/personal/miguel_gonzalez_med_usc_edu/IQBOUo8yT_7MQ5MvTlv5MvcvAciCV_5EvAhQJMZTn1jqso4"

def run_pipeline():
    all_dfs = []
    
    # Target tab name containing columns: Site Name, Service Date, Weight (lbs), Cost
    target_sheet = "RawData" 
    
    # 1. Pull from live URL
    print("Pulling live data from SharePoint...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
    }
    try:
        res = requests.get(sharepoint_url, headers=headers)
        if res.status_code == 200:
            # io.BytesIO prevents the deprecation warning and handles raw streams cleanly
            df_online = pd.read_excel(io.BytesIO(res.content), sheet_name=target_sheet, engine='openpyxl')
            all_dfs.append(df_online)
            print(f"Loaded live SharePoint data successfully: {len(df_online)} rows pulled.")
    except Exception as e:
        print(f"URL pull skipped or encountered parsing limits: {e}")

    # 2. Add local folder dumps
    if os.path.exists("raw_data_inputs"):
        files = glob.glob("raw_data_inputs/*.xlsx") + glob.glob("raw_data_inputs/*.xls")
        for f in files:
            try:
                # Explicitly target 'RawData' tab inside your manual file drops as well
                df_local = pd.read_excel(f, sheet_name=target_sheet, engine='openpyxl')
                all_dfs.append(df_local)
                print(f"Successfully loaded local file '{os.path.basename(f)}': {len(df_local)} rows.")
            except Exception as e:
                print(f"Could not read sheet '{target_sheet}' from file {os.path.basename(f)}: {e}")

    if not all_dfs:
        print("Error: No data collections matched execution parameters.")
        return

    # Combine data structures 
    df = pd.concat(all_dfs, ignore_index=True)
    
    # Drop rows that are entirely blank or have no structural column definition
    df.dropna(how='all', inplace=True)
    
    # Standardize column headers by trimming accidental trailing whitespaces
    df.columns = df.columns.str.strip()
    
    # Validate critical target columns exist before mathematical processing
    required_cols = ['Service Date', 'Site Name', 'Weight (lbs)', 'Cost']
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Missing required data column: '{col}'. Check your spreadsheet header labels.")

    # Drop exact duplicate records across consolidated assets
    df.drop_duplicates(inplace=True)
    
    # Clean dates and transform fields to standard metrics
    df['Service Date'] = pd.to_datetime(df['Service Date'], errors='coerce')
    df = df.dropna(subset=['Service Date'])
    
    df['Weight (lbs)'] = pd.to_numeric(df['Weight (lbs)'], errors='coerce').fillna(0)
    df['Cost'] = pd.to_numeric(df['Cost'], errors='coerce').fillna(0)
    
    # Format a Month-Year tracking dimension (YYYY-MM)
    df['MonthYear'] = df['Service Date'].dt.to_period('M').astype(str)
    
    # 3. Compile Aggregate Analytics Objects
    total_lbs = float(df['Weight (lbs)'].sum())
    total_cost = float(df['Cost'].sum())
    
    # Site aggregation
    site_breakdown = df.groupby('Site Name').agg(
        lbs=('Weight (lbs)', 'sum'),
        cost=('Cost', 'sum')
    ).reset_index().to_dict(orient='records')
    
    # Chronological timeline monthly aggregation
    timeline = df.groupby('MonthYear').agg(
        lbs=('Weight (lbs)', 'sum'),
        cost=('Cost', 'sum')
    ).sort_index().reset_index().to_dict(orient='records')
    
    # Final structured packaging payload for index.html consumption
    dashboard_payload = {
        "kpis": {
            "total_weight_lbs": round(total_lbs, 1),
            "total_cost_usd": round(total_cost, 2),
            "total_records": len(df)
        },
        "site_breakdown": site_breakdown,
        "monthly_timeline": timeline
    }
    
    with open("dashboard_data.json", "w") as f:
        json.dump(dashboard_payload, f, indent=4)
        
    print(f"Data consolidation successful. {len(df)} total unique tracking line items compiled.")

if __name__ == "__main__":
    run_pipeline()
