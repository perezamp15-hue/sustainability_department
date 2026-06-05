import pandas as pd
import json
import os
import glob

def run_surgery_pipeline():
    # Look for our target workbook file
    workbook_name = "Main OR Case Times-4.xlsx"
    
    # Locate file path in root or inputs directory
    target_file = None
    if os.path.exists(workbook_name):
        target_file = workbook_name
    elif os.path.exists(f"raw_data_inputs/{workbook_name}"):
        target_file = f"raw_data_inputs/{workbook_name}"
    else:
        # Fallback to scanning for any uploaded .xlsx files if named differently
        xlsx_files = glob.glob("*.xlsx") + glob.glob("raw_data_inputs/*.xlsx")
        if xlsx_files:
            target_file = xlsx_files[0]
            
    if not target_file:
        print(f"Error: Could not locate master workbook file '{workbook_name}'")
        return

    print(f"Parsing clinical metrics from: {target_file}")
    
    # 1. Read and Aggregate Biohazard Waste Weights
    try:
        df_waste = pd.read_excel(target_file, sheet_name="Biowaste_Raw_Data", engine='openpyxl')
    except Exception as e:
        print(f"Failed to read sheet 'Biowaste_Raw_Data'. Error: {e}")
        return

    # Standardize column formatting strings
    df_waste.columns = df_waste.columns.str.strip()
    df_waste['Weight (lbs)'] = pd.to_numeric(df_waste['Weight (lbs)'], errors='coerce').fillna(0)
    df_waste['Month'] = df_waste['Month'].astype(str).str.strip()
    df_waste['Year'] = df_waste['Year'].astype(str).str.strip()
    
    # Sum up overall biohazard weights grouped by Year and Month
    waste_grouped = df_waste.groupby(['Year', 'Month'])['Weight (lbs)'].sum().reset_index()

    # 2. Read and Aggregate Total Surgical Duration Hours
    try:
        df_surgery = pd.read_excel(target_file, sheet_name="OR_Cases_Raw_Data", engine='openpyxl')
    except Exception as e:
        print(f"Failed to read sheet 'OR_Cases_Raw_Data'. Error: {e}")
        return

    df_surgery.columns = df_surgery.columns.str.strip()
    df_surgery['Surgery Length (Hours)'] = pd.to_numeric(df_surgery['Surgery Length (Hours)'], errors='coerce').fillna(0)
    df_surgery['Month'] = df_surgery['Month'].astype(str).str.strip()
    df_surgery['Year'] = df_surgery['Year'].astype(str).str.strip()

    # Sum total hours grouped by Year and Month
    surgery_grouped = df_surgery.groupby(['Year', 'Month'])['Surgery Length (Hours)'].sum().reset_index()

    # 3. Merge the datasets on time dimensions
    merged = pd.merge(waste_grouped, surgery_grouped, on=['Year', 'Month'], how='inner')
    
    if merged.empty:
        print("Warning: Chronological merging returned empty matrix. Check spelling consistency of Month names.")
        return

    # 4. Calculate target efficiency ratio formula: (0.7 * Biohazard Weight) / Total Surgery Hours
    merged['Calculated_Metric'] = (0.7 * merged['Weight (lbs)']) / merged['Surgery Length (Hours)']
    
    # Standardize textual timeline labels for frontend bar grouping (e.g. "October 2024")
    merged['Label'] = merged['Month'] + " " + merged['Year']
    
    # Create an explicit chronological sorting key helper value
    month_order = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
        'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    merged['Month_Num'] = merged['Month'].map(month_order).fillna(1)
    merged['Year_Num'] = pd.to_numeric(merged['Year'], errors='coerce').fillna(2024)
    merged = merged.sort_values(by=['Year_Num', 'Month_Num']).drop(columns=['Month_Num', 'Year_Num'])

    # Format into web data structures
    output_records = []
    for _, row in merged.iterrows():
        output_records.append({
            "label": str(row['Label']),
            "bio_weight": float(row['Weight (lbs)']),
            "surg_hours": float(row['Surgery Length (Hours)']),
            "metric": round(float(row['Calculated_Metric']), 4)
        })

    with open("surgery_efficiency_data.json", "w") as f:
        json.dump(output_records, f, indent=4)
        
    print(f"Success! Extracted {len(output_records)} monthly analysis nodes into 'surgery_efficiency_data.json'")

if __name__ == "__main__":
    run_surgery_pipeline()
