import json
import os
import requests
from flask import Flask, render_template, request, jsonify, send_file
from fairseq_asr import asr_result
import single_file_inference as infer
from main import getConversationFormatFromWav
import pandas as pd
import uuid
import time
from single_file_inference import Wav2VecCtc
from flask import request, jsonify
from functions import AudioUtils,TranscriptHandler,SentimentProcessor,FileHandler
from logging_setup import logger_level

app = Flask(__name__, template_folder='../frontend/templates')  # Adjust the template folder path
SERVER2_BASE_URL = "http://192.168.30.186:8002"  # Replace with the actual URL of your server2
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
logger_info  = logger_level("INFO", filename=os.path.basename(__file__))
logger_debug  = logger_level("DEBUG", filename=os.path.basename(__file__))
logger_error = logger_level("ERROR", filename=os.path.basename(__file__))
logger_warning = logger_level("WARNING", filename=os.path.basename(__file__))
logger_critical = logger_level("CRITICAL",filename=os.path.basename(__file__))

@app.route('/')
def index():
 return render_template('index.html')

@app.route('/upload', methods=['POST', 'GET'])
def upload_file():
    start_time = time.time()  # Record start time
    file_path = None

    try:
        if 'file' in request.files:
            logger_info.info("Received file upload request.")
            uploaded_file = request.files['file']

            # Validate file size
            if not FileHandler.validate_file_size(uploaded_file, 30 * 1024 * 1024):  # 30 MB limit
                logger_warning.warning("Uploaded file exceeds the 30 MB size limit.")
                return jsonify({"error": "Uploaded file exceeds the 30 MB size limit."}), 400

            # Save file
            file_path = FileHandler.save_uploaded_file(uploaded_file)
            logger_info.info(f"File saved at {file_path}")

        elif 'audio_url' in request.form:
            audio_url = request.form['audio_url']
            output_directory = os.path.join(PROJECT_ROOT, "uploads")
            logger_info.info(f"Processing audio URL: {audio_url}")

            try:
                file_path = AudioUtils.download_and_convert_to_wav(audio_url, output_directory)
                logger_info.info("Audio file downloaded and converted successfully.")
            except ValueError as ve:
                logger_error.error(f"ValueError: {str(ve)}")
                return jsonify({"error": str(ve)}), 400
            except RuntimeError as re:
                logger_error.error(f"RuntimeError: {str(re)}")
                return jsonify({"error": str(re)}), 500
        else:
            logger_warning.warning("No file or audio URL provided.")
            return jsonify({"error": "No file or audio URL provided."}), 400

        # Validate file format
        if not FileHandler.validate_audio_format(file_path):
            logger_error.error("Invalid file format. Only MP3 and WAV files are supported.")
            return jsonify({"error": "Invalid file format. Please upload an MP3 or WAV file."}), 400

        # Convert MP3 to WAV if necessary
        file_path = FileHandler.convert_to_wav_if_needed(file_path)

        # Process audio
        rttm_data = diarize_on_server2(file_path)
        final_result, json_file_path = asr_result(file_path, rttm_data, "en")

        # Extract transcript-related data
        transcipt_conf_score = TranscriptHandler.get_transcripts_with_confidence(json_file_path)
        data = {
            "transcriptions": TranscriptHandler.get_all_transcriptions(json_file_path),
            "agent_transcript": TranscriptHandler.extract_agent_transcripts(json_file_path),
            "customer_transcript": TranscriptHandler.extract_customer_transcripts(json_file_path),
            "alternatives": SentimentProcessor.combine_data(transcipt_conf_score)[1],
            "utterances": SentimentProcessor.combine_data(transcipt_conf_score)[0],
            "call_duration": AudioUtils.get_audio_duration(file_path),
            "silence/hold_duration": 121.98,
            "silence/hold_percentage": 39.045,
            "audio_file_name": os.path.basename(file_path),
            "id": str(uuid.uuid4()),
        }

        return jsonify(data), 200

    except FileNotFoundError as e:
        logger_error.error(f"File not found: {str(e)}")
        return jsonify({"error": f"File not found: {str(e)}"}), 500
    except Exception as e:
        logger_error.exception("An unexpected error occurred.")
        return jsonify({"error": str(e)}), 500
    

@app.route('/download_json', methods=['GET'])
def download_json():
    file_path = request.args.get('file_path', type=str)
    logger_info.info(f"Received request to download JSON file: {file_path}")
    return send_file(file_path, as_attachment=True)

def asr_result(wav_path, rttm_data, language):
    logger_info.info(f"Processing ASR result for file: {wav_path}")
    wav_directory = os.path.dirname(wav_path)
    excel_name = os.path.basename(wav_path).split('.')[0]
    conversation_format, act_dict = getConversationFormatFromWav(wav_path, rttm_data, language)
    logger_debug.debug(f"Conversation format extracted")
    df = pd.DataFrame(conversation_format)
    if act_dict:
        df["speaker_id"] = df["speaker_id"].replace(act_dict)
        logger_debug.debug("Speaker IDs replaced with mapped values.")
    json_file_path = os.path.join(wav_directory, f'{excel_name}.json')
    if os.path.exists(json_file_path):
        logger_warning.warning(f"Overwriting existing JSON file: {json_file_path}")
        os.remove(json_file_path)
    df.to_json(json_file_path, orient='records', indent=4)
    logger_info.info(f"ASR result saved to JSON: {json_file_path}")
    return df, json_file_path


def diarize_on_server2(file_path):
    try:
        logger_info.info(f"Sending request to Server 2 for diarization: {file_path}")
        diarization_url = f"{SERVER2_BASE_URL}/diarize"
        data = {"wav_path": file_path}
        response = requests.post(diarization_url, json=data)
        response.raise_for_status()
        rttm_data = response.text
        logger_info.info("Successfully received diarization data from Server 2")
        return rttm_data
    except requests.exceptions.RequestException as e:
        logger_error.error(f"Failed to communicate with Server 2: {str(e)}")
        raise


if __name__ == '__main__':
    infer.start_all(PROJECT_ROOT + "/languages")
    app.run(host='0.0.0.0',debug=False, port=10003)

