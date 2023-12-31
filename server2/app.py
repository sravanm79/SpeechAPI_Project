import os.path

from flask import Flask, request, jsonify, send_file
from pynnote_diarization import diarize_speaker

app = Flask(__name__)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


@app.route('/diarize', methods=['POST'])
def diarize_file():
    try:
        data = request.json
        wav_path = data.get('wav_path')
        print(wav_path)
        if not os.path.exists(wav_path):
            raise ValueError("WAV path not exists")

        rttm_data = diarize_speaker(wav_path)
        rttm_file_path = f"{PROJECT_ROOT}/uploads/rttm_files/{os.path.basename(wav_path)[:-4]}.rttm"
        with open(rttm_file_path, 'w') as file:
            rttm_data.write_rttm(file)
        return send_file(rttm_file_path)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
