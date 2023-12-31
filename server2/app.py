from flask import Flask, request, jsonify, Response
from pynnote_diarization import diarize_speaker

app = Flask(__name__)


@app.route('/diarize', methods=['POST'])
def diarize_file():
    try:
        data = request.json
        wav_path = data.get('wav_path')

        if not wav_path:
            raise ValueError("WAV path not provided")

        rttm_data = diarize_speaker(wav_path)
        return Response(rttm_data, mimetype='text/plain')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
