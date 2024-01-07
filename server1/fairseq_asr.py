# Import Fairseq ASR module and define process_audio function
# Use the Fairseq ASR model to transcribe audio chunks
# Combine transcriptions and speaker labels
# Generate final JSON output
import os
import pandas as pd

from main import getConversationFormatFromWav


def asr_result(wav_path, rttm_data, language):
    wav_directory = os.path.dirname(wav_path)
    conversation_format, act_dict = getConversationFormatFromWav(wav_path, rttm_data, language)
    df = pd.DataFrame(conversation_format)
    if act_dict != {}:
        df["speaker_id"] = df["speaker_id"].replace(act_dict)
    excel_file_path = os.path.join(wav_directory, "conversation_data.xlsx")
    df.to_excel(excel_file_path, index=False)
    return df.to_dict(), excel_file_path
