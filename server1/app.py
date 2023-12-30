from flask import Flask, render_template, request, jsonify
from fairseq_asr import process_audio

app = Flask(__name__)

app = Flask(__name__, template_folder='../frontend/templates')

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']

    #getrttmfromServer2
    result = process_audio()

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
