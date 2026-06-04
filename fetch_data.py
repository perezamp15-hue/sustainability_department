import pandas as pd
import json
import os
import glob
import requests

sharepoint_url = "https://keckmedicine-my.sharepoint.com/personal/miguel_gonzalez_med_usc_edu/_layouts/15/download.aspx?SourceUrl=https://keckmedicine-my.sharepoint.com/personal/miguel_gonzalez_med_usc_edu/:x:/g/personal/miguel_gonzalez_med_usc_edu/IQBOUo8yT_7MQ5MvTlv5MvcvAciCV_5EvAhQJMZTn1jqso4"

def run_pipeline():
    all_dfs = []
    
    # 1. Pull from live URL
    print("Pulling live data...")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(sharepoint_url, headers=headers)
        if res.status_code == 200:
            all_dfs.append(pd.read_excel(res.content, engine='openpyxl'))
    except Exception as e:
        print(f"URL failed: {e}")

    # 2. Add local folder dumps
    if os.path.exists("raw_data_inputs"):
        files = glob.glob("raw_data_inputs/*.xlsx") + glob.glob("raw_data_inputs/*.xls")
        for f in files:
            try:
                all_dfs.append(pd.read_excel(f, engine='openpyxl'))
            except Exception as e:
                print(f"Error reading local file {f}: {e}")

    if not all_dfs:
        print("No data available.")
        return

    # Combine everything and drop duplicate rows
    df = pd.concat(all_dfs, ignore_index=True)
    df.drop_duplicates(inplace=True)
    
    # Clean up dates and values
    df['Service Date'] = pd.to_datetime(df['Service Date'], errors='coerce')
    df = df.dropna(subset=['Service Date'])
    df['Weight (lbs)'] = pd.to_numeric(df['Weight (lbs)'], errors='coerce').fillna(0)
    df['Cost'] = pd.to_numeric(df['Cost'], errors='coerce').fillna(0)
    
    # Extract Month/Year identifier for timelines
    df['MonthYear'] = df['Service Date'].dt.to_period('M').astype(str)
    
    # 3. Create Dashboard Core Analytics
    total_lbs = float(df['Weight (lbs)'].sum())
    total_cost = float(df['Cost'].sum())
    
    # Break down metrics by Facility Site
    site_breakdown = df.groupby('Site Name').agg(
        lbs=('Weight (lbs)', 'sum'),
        cost=('Cost', 'sum')
    ).reset_index().to_dict(orient='records')
    
    # Break down historical monthly timeline patterns
    timeline = df.groupby('MonthYear').agg(
        lbs=('Weight (lbs)', 'sum'),
        cost=('Cost', 'sum')
    ).sort_index().reset_index().to_dict(orient='records')
    
    # Export structure optimized for the web frontend
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
    print("Dashboard payload successfully compiled!")

if __name__ == "__main__":
    run_pipeline()
