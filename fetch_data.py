import pandas as pd
import requests
import json
import os
import glob

# Online SharePoint config
base_sharepoint = "https://keckmedicine-my.sharepoint.com/personal/miguel_gonzalez_med_usc_edu"
doc_path = ":x:/g/personal/miguel_gonzalez_med_usc_edu/IQBOUo8yT_7MQ5MvTlv5MvcvAciCV_5EvAhQJMZTn1jqso4"
sharepoint_url = f"{base_sharepoint}/_layouts/15/download.aspx?SourceUrl={base_sharepoint}/{doc_path}"

def run_pipeline():
    all_dataframes = []
    
    # 1. FETCH THE ONLINE LIVE SHAREPOINT FILE
    print("Fetching live data from SharePoint...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    try:
        response = requests.get(sharepoint_url, headers=headers)
        if response.status_code == 200:
            df_sharepoint = pd.read_excel(response.content, engine='openpyxl')
            all_dataframes.append(df_sharepoint)
            print(f"Loaded live SharePoint file: {len(df_sharepoint)} rows.")
    except Exception as e:
        print(f"Warning: Could not fetch online SharePoint data: {e}. Moving to local files.")

    # 2. SCAN AND LOAD ALL LOCAL EXCEL FILES
    folder_path = "raw_data_inputs"
    
    # Ensure folder exists so script doesn't crash on first run
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created '{folder_path}' folder. Drop local Excel files here in the future.")
        
    # Search for any .xlsx or .xls files in that folder
    excel_files = glob.glob(os.path.join(folder_path, "*.xlsx")) + glob.glob(os.path.join(folder_path, "*.xls"))
    
    print(f"Found {len(excel_files)} local files to consolidate.")
    for file in excel_files:
        try:
            df_local = pd.read_excel(file, engine='openpyxl')
            all_dataframes.append(df_local)
            print(f"Successfully loaded local file '{os.path.basename(file)}': {len(df_local)} rows.")
        except Exception as e:
            print(f"Error loading file {file}: {e}")

    # 3. MERGE, CLEAN, AND REMOVE DUPLICATES
    if not all_dataframes:
        print("No data found to process.")
        return

    # Combine everything into one single massive dataframe
    master_df = pd.concat(all_dataframes, ignore_index=True)
    initial_count = len(master_df)
    
    # Drop rows where every single column is empty
    master_df.dropna(how='all', inplace=True)
    
    # CRITICAL: Removes duplicate rows across your files
    master_df.drop_duplicates(inplace=True)
    final_count = len(master_df)
    
    print(f"Consolidation complete! Merged {initial_count} rows down to {final_count} unique rows.")

    # 4. SAVE OUTPUT
    transformed_data = master_df.to_dict(orient="records")
    with open("dashboard_data.json", "w") as f:
        json.dump(transformed_data, f, indent=4)
        
    print("Master dataset saved to dashboard_data.json")

if __name__ == "__main__":
    run_pipeline()
