import os
import requests
from flask import Flask, render_template, request, jsonify
from fairseq_asr import asr_result

app = Flask(__name__, template_folder='../frontend/templates')  # Adjust the template folder path
SERVER2_BASE_URL = "http://localhost:8001"  # Replace with the actual URL of your server2


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        uploaded_file = request.files['file']
        file_path = f"./uploads/{uploaded_file.filename}"
        uploaded_file.save(file_path)

        rttm_file_path = diarize_on_server2(file_path)

        # Perform Fairseq ASR on the chunks using the RTTM file
        final_result = asr_result(file_path, rttm_file_path)

        return jsonify(final_result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up: remove the uploaded file
        os.remove(file_path)


def diarize_on_server2(file_path):
    try:
        diarization_url = f"{SERVER2_BASE_URL}/diarize"
        files = {'file': open(file_path, 'rb')}
        response = requests.post(diarization_url, files=files)
        response.raise_for_status()
        rttm_file_path = f"./uploads/{os.path.basename(file_path)[:-4]}.rttm"
        with open(rttm_file_path, 'wb') as f:
            f.write(response.content)

        return rttm_file_path
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to communicate with Server 2: {str(e)}")


def merge_results(asr_result, diarization_result):
    # Implement merging logic based on your requirements
    # For example, combine speaker information from diarization with ASR transcriptions
    merged_result = {"asr": asr_result, "diarization": diarization_result}
    return merged_result


if __name__ == '__main__':
    app.run(debug=True,port=8001)
