from flask import Flask, request, jsonify
from pynnote_diarization import diarize_speaker

app = Flask(__name__)


@app.route('/diarize', methods=['POST'])
def diarize_file():
    try:
        data = request.json
        wav_path = data.get('wav_path')

        if not wav_path:
            raise ValueError("WAV path not provided")

        rttm_result_path = diarize_speaker(wav_path)
        return jsonify({"rttm_result_path": rttm_result_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
