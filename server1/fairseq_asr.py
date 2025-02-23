import os
import pandas as pd
import json

from main import getConversationFormatFromWav

def asr_result(wav_path, rttm_data, language):
    wav_directory = os.path.dirname(wav_path)
    print(os.path.basename(wav_path))
    excel_name = os.path.basename(wav_path).split('.')[0]
    conversation_format, act_dict = getConversationFormatFromWav(wav_path, rttm_data, language)
    df = pd.DataFrame(conversation_format)
    if act_dict != {}:
        df["speaker_id"] = df["speaker_id"].replace(act_dict)
    json_file_path = os.path.join(wav_directory, excel_name + '.json')  # Change the extension to .json
    if os.path.exists(json_file_path):
        os.remove(json_file_path)
    # Convert DataFrame to JSON with 'records' orientation and indent for pretty formatting
    json_data = df.to_json(orient='records', indent=4)

    # Write JSON data to file
    with open(json_file_path, 'w') as json_file:
        json.dump(json_data, json_file)

    return df, json_file_path

