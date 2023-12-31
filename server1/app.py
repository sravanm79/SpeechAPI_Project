import os
import requests
from flask import Flask, render_template, request, jsonify
from fairseq_asr import asr_result
import single_file_inference as infer
from single_file_inference import Wav2VecCtc

app = Flask(__name__, template_folder='../frontend/templates')  # Adjust the template folder path
SERVER2_BASE_URL = "http://localhost:8002"  # Replace with the actual URL of your server2
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        uploaded_file = request.files['file']
        file_path = f"{PROJECT_ROOT}/uploads/{uploaded_file.filename}"
        uploaded_file.save(file_path)

        rttm_data = diarize_on_server2(file_path)

        # Perform Fairseq ASR on the chunks using the RTTM file
        final_result = asr_result(file_path, rttm_data)
        return jsonify(final_result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up: remove the uploaded file
        os.remove(file_path)


def diarize_on_server2(file_path):
    try:
        diarization_url = f"{SERVER2_BASE_URL}/diarize"
        data = {"wav_path": file_path}

        response = requests.post(diarization_url, json=data)
        response.raise_for_status()
        rttm_data = response.text
        return rttm_data
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to communicate with Server 2: {str(e)}")


if __name__ == '__main__':
    infer.start_all(PROJECT_ROOT+"/languages")
    app.run(port=8001)
