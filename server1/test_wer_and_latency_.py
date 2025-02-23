import numpy as np
import pandas as pd
import os


def excel_to_txt(excel_file):
    sheetA = pd.read_excel(excel_file, sheet_name=0)  # Read the first sheet
    sheet3 = pd.read_excel(excel_file, sheet_name=2)  # Read the third sheet

# Ensure the required columns exist in Sheet 1
if 'Filename' not in sheet1.columns or 'Request_id' not in sheet1.columns:
    raise ValueError("Sheet 1 must contain 'Filename' and 'Request_id' columns.")

# Handle column name variations in Sheet 3
if 'request_id' in sheet3.columns and 'transcript' in sheet3.columns:
    sheet3.rename(columns={'request_id': 'Request_id'}, inplace=True)  # Standardize column name
elif 'Request_id' not in sheet3.columns or 'transcript' not in sheet3.columns:
    raise ValueError("Sheet 3 must contain 'request_id' or 'Request_id' and 'transcript' columns.")

# Merge the two sheets based on 'Request_id'
merged_data = pd.merge(sheet1, sheet3, on='Request_id')

# Specify the folder where text files will be saved
output_folder = "/content/drive/MyDrive/Test data/FLIPKART_/30-05-2024/txt_files"

# Create the folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Loop through the merged data and create text files
for _, row in merged_data.iterrows():
    filename = os.path.join(output_folder, f"{row['Filename']}.txt")
    transcript = row['transcript']

    # Write the transcript to a text file
    with open(filename, "w", encoding="utf-8") as file:
        file.write(transcript)

print(f"Text files created successfully in the folder '{output_folder}'!")
