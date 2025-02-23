import json
import os
import requests
from flask import Flask, render_template, request, jsonify, send_file
from fairseq_asr import asr_result
import single_file_inference as infer
from pydub import AudioSegment
from main import getConversationFormatFromWav
import pandas as pd
import uuid
import time
import hashlib
import subprocess
import audioread
from single_file_inference import Wav2VecCtc
from old_functions import get_transcripts_with_confidence, get_all_transcriptions, extract_agent_transcripts, extract_customer_transcripts, combine_data,get_audio_duration
from flask import request, jsonify
from pydub import AudioSegment
from flask import copy_current_request_context
from concurrent.futures import ThreadPoolExecutor
#from speechbrain.pretrained.interfaces import foreign_class
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
    start_time = time.time()  # Record the start time
    audio_uploaded = False
    rttm_uploaded = False
    file_path = None

    try:
        if 'file' in request.files:  # Check if an audio file is uploaded
            logger_info.info("Received request to /upload")
            uploaded_file = request.files['file']

                    # Check file size
            uploaded_file.seek(0, os.SEEK_END)  # Move to the end of the file
            file_size = uploaded_file.tell()  # Get the size of the file
            print("file_size", file_size)
            uploaded_file.seek(0)  # Reset the file pointer to the beginning

            if file_size > 30 * 1024 * 1024:  # Check if the file size is greater than 10 MB
                logger_warning.warning("Uploaded file exceeds the 30 MB size limit.")
                return jsonify({"error": "Uploaded file exceeds the 5 MB size limit."}), 400
            
            # Save the file for processing
            file_path = f"{PROJECT_ROOT}/uploads/{uploaded_file.filename}"
            uploaded_file.save(file_path)
            logger_info.info(f"File saved at {file_path}")
        elif 'audio_url' in request.form:  # Check if a URL is provided
            audio_url = request.form['audio_url']
            output_directory = os.path.join(PROJECT_ROOT, "uploads")
            logger_info.info(f"Processing audio URL: {audio_url}")
            print(f"Processing URL: {audio_url}")

            # Call the download and conversion function
            try:
                file_path = download_and_convert_to_wav(audio_url, output_directory)
                logger_info.info("Audio file downloaded and converted successfully.")
                print("response_from_functioj", file_path)
            except ValueError as ve:
                logger_error.error(f"ValueError: {str(ve)}")
                return jsonify({"error": str(ve)}), 400
            except RuntimeError as re:
                logger_error.error(f"RuntimeError: {str(re)}")
                return jsonify({"error": str(re)}), 500


        else:
            logger_warning.warning("No file or audio URL provided.")
            return jsonify({"error": "No file or audio URL provided."}), 400

        language = "en"
        
        valid_extensions = ('.mp3', '.wav')
        
        if not file_path.lower().endswith(valid_extensions):
            logger_error.error("Invalid file format. Only MP3 and WAV files are supported.")
            raise ValueError("Invalid file format. Please upload an MP3 or WAV file.")

        # If the file is not already in WAV format, convert it
        if file_path.lower().endswith('.mp3'):
            logger_debug.debug("Converting MP3 to WAV format.")
            sound = AudioSegment.from_mp3(file_path)
            file_path = file_path.replace(".mp3", ".wav")
            sound.export(file_path, format="wav")
            logger_info.info("Conversion completed successfully.")

        # Process the file
        rttm_data = diarize_on_server2(file_path)

        final_result, json_file_path = asr_result(file_path, rttm_data, language)

        html_output = final_result.to_html()
        json_data = json.dumps(final_result.to_dict(orient='records'))
        print("json_file_path", json_file_path)
        transcipt_conf_score = get_transcripts_with_confidence(json_file_path)
        all_transcriptions = get_all_transcriptions(json_file_path)
        agent_transcript = extract_agent_transcripts(json_file_path)
        customer_transcript = extract_customer_transcripts(json_file_path)
        combined_data_all, words_data = combine_data(transcipt_conf_score)
        # print(transcipt_conf_score)
        print("audio_file_path", file_path)
        call_duration = get_audio_duration(file_path)
        file_name = os.path.basename(file_path)
        data = {
            "transcriptions": all_transcriptions,
            "agent_transcript": agent_transcript,
            "customer_transcript": customer_transcript,
            "alternatives": words_data,
            "utterances": combined_data_all,
            "call_duration" : call_duration,
            "silence/hold_duration":121.98,
            "silence/hold_percentage":39.045,
            "audio_file_name":file_name,
            "id": str(uuid.uuid4())

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


def download_and_convert_to_wav(audio_url, output_directory):
    try:
        logger_info.info(f"Starting download of audio file from: {audio_url}")
        os.makedirs(output_directory, exist_ok=True)

        # Generate a unique file name using the URL hash
        url_hash = hashlib.md5(audio_url.encode('utf-8')).hexdigest()
        file_extension = os.path.splitext(audio_url.split("?")[0])[-1] or ".unknown"
        sanitized_file_name = f"audio_{url_hash}{file_extension}"
        original_file_path = os.path.join(output_directory, sanitized_file_name)
        logger_debug.debug(f"Generated file path: {original_file_path}")

        # Check if URL returns a valid audio file
        head_response = requests.head(audio_url, allow_redirects=True)
        content_type = head_response.headers.get('Content-Type', '')
        if 'audio' not in content_type and content_type != 'application/octet-stream':
            logger_warning.warning("Content-Type does not indicate an audio file. Proceeding with caution.")

        # Download the file
        response = requests.get(audio_url, stream=True)
        if response.status_code == 200:
            with open(original_file_path, 'wb') as audio_file:
                for chunk in response.iter_content(chunk_size=8192):
                    audio_file.write(chunk)
            logger_info.info(f"File downloaded successfully: {original_file_path}")
        else:
            logger_error.error(f"Failed to download audio. Status code: {response.status_code}")
            # raise ValueError(f"Failed to download audio. Status code: {response.status_code}")
            return None
        
                # Ensure file exists and is not empty
        if not os.path.exists(original_file_path) or os.path.getsize(original_file_path) == 0:
            logger_error.error(f"Downloaded file is missing or empty: {original_file_path}")
            return None  # Skip this iteration


        # Check if the file is already a WAV file
        if original_file_path.lower().endswith('.wav'):
            logger_info.info(f"File is already in WAV format: {original_file_path}")
            wav_file_path = original_file_path
        else:
            wav_file_path = os.path.join(output_directory, f"{os.path.splitext(sanitized_file_name)[0]}.wav")
            logger_debug.debug(f"Attempting to convert file to WAV: {wav_file_path}")

            # Detect format using audioread
            try:
                with audioread.audio_open(original_file_path) as f:
                    detected_format = f.format
                logger_info.info(f"Detected format: {detected_format}")
            except Exception as e:
                logger_warning.warning(f"Could not detect format with audioread: {e}")
                detected_format = None

            # Convert using pydub (FFmpeg)
            try:
                audio = AudioSegment.from_file(original_file_path, format=detected_format)
                audio.export(wav_file_path, format="wav")
                logger_info.info(f"File converted to WAV using pydub: {wav_file_path}")
            except Exception as e:
                logger_error.error(f"pydub failed: {e}. Trying FFmpeg.")

                # Fallback to FFmpeg CLI
                ffmpeg_cmd = ["ffmpeg", "-y", "-i", original_file_path, wav_file_path]
                result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    logger_error.error(f"FFmpeg conversion failed: {result.stderr.decode()}")
                    raise RuntimeError(f"FFmpeg failed: {result.stderr.decode()}")
                logger_info.info(f"File converted to WAV using FFmpeg: {wav_file_path}")

            # Final fallback to SoX
            if not os.path.exists(wav_file_path):
                logger_warning.warning("FFmpeg failed. Trying SoX.")
                sox_cmd = ["sox", original_file_path, wav_file_path]
                result = subprocess.run(sox_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    logger_error.error(f"SoX conversion failed: {result.stderr.decode()}")
                    raise RuntimeError(f"SoX failed: {result.stderr.decode()}")
                logger_info.info(f"File converted to WAV using SoX: {wav_file_path}")

        # Check final file size
        # if os.path.getsize(wav_file_path) > 30 * 1024 * 1024:
        #     os.remove(wav_file_path)
        #     logger_info.error("Converted WAV file exceeds the 30 MB size limit.")
        #     raise ValueError("Converted WAV file exceeds the 30 MB size limit.")

        logger_info.info(f"Returning WAV file path: {wav_file_path}")
        return wav_file_path

    except requests.exceptions.RequestException as req_err:
        logger_error.error(f"Error during file download: {str(req_err)}")
        raise RuntimeError(f"Error during file download: {str(req_err)}")
    except Exception as e:
        logger_error.error(f"Error during download or conversion: {str(e)}")
        raise RuntimeError(f"Error during download or conversion: {str(e)}")

if __name__ == '__main__':
    infer.start_all(PROJECT_ROOT + "/languages")
    app.run(host='0.0.0.0',debug=False, port=10003)

