import os
import pandas as pd

def convert_csvs_to_excel(directory):
    """
    Converts all CSV files in the given directory to Excel (.xlsx)
    and deletes the original CSV file after conversion.
    """
    for filename in os.listdir(directory):
        if filename.lower().endswith(".csv"):
            csv_path = os.path.join(directory, filename)

            # Load CSV into DataFrame
            df = pd.read_csv(csv_path)

            # Create Excel filename
            excel_filename = filename[:-4] + ".xlsx"
            excel_path = os.path.join(directory, excel_filename)

            # Save to Excel
            df.to_excel(excel_path, index=False)

            # Delete old CSV
            os.remove(csv_path)

            print(f"Converted: {filename} → {excel_filename}")

# Example usage
convert_csvs_to_excel(r"C:\Users\pm018586\OneDrive - Zelis Healthcare\Documents\Tasks\RUST_VS_PYTHON\BENCHMARKING\locust_output\python")
