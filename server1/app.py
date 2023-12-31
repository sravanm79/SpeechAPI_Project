import os
import requests
from flask import Flask, render_template, request, jsonify
from fairseq_asr import asr_result

app = Flask(__name__, template_folder='../frontend/templates')  # Adjust the template folder path
SERVER2_BASE_URL = "http://localhost:5000"  # Replace with the actual URL of your server2


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        uploaded_file = request.files['file']
        file_path = f"../uploads/{uploaded_file.filename}"
        uploaded_file.save(file_path)

        rttm_data = diarize_on_server2(file_path)

        # Perform Fairseq ASR on the chunks using the RTTM file


        return jsonify(rttm_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up: remove the uploaded file
        os.remove(file_path)


def diarize_on_server2(file_path):
    try:
        diarization_url = f"{SERVER2_BASE_URL}/diarize"
        abs_path = str(os.path.abspath(file_path))
        data = {"wav_path": abs_path}

        response = requests.post(diarization_url, json=data)
        response.raise_for_status()
        rttm_data = response.text
        return rttm_data
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to communicate with Server 2: {str(e)}")


def merge_results(asr_result, diarization_result):
    # Implement merging logic based on your requirements
    # For example, combine speaker information from diarization with ASR transcriptions
    merged_result = {"asr": asr_result, "diarization": diarization_result}
    return merged_result


if __name__ == '__main__':
    app.run(debug=True, port=8001)
