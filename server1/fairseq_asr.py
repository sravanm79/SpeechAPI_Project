# Import Fairseq ASR module and define process_audio function
# Use the Fairseq ASR model to transcribe audio chunks
# Combine transcriptions and speaker labels
# Generate final JSON output
from main import getConversationFormatFromWav


def asr_result(wav_path, rttm_data):
    conversation_format = getConversationFormatFromWav(wav_path,rttm_data)
    return conversation_format
