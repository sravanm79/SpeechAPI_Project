from pydub import AudioSegment
import json
import uuid
from flask import Flask
import os
from logging_setup import logger_level
import hashlib
import subprocess
import requests
import audioread
logger_info  = logger_level("INFO", filename=os.path.basename(__file__))
logger_debug  = logger_level("DEBUG", filename=os.path.basename(__file__))
logger_error = logger_level("ERROR", filename=os.path.basename(__file__))
logger_warning = logger_level("WARNING", filename=os.path.basename(__file__))
logger_critical = logger_level("CRITICAL",filename=os.path.basename(__file__))
app = Flask(__name__)

# Constants
STOP_WORDS = set([
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd",
    'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers',
    'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
    'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if',
    'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
    'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out',
    'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
    'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't",
    'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn',
    "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't",
    'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't",
    'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't", "give",
    "take"
])


# Define a function to calculate the duration of the audio file
def get_audio_duration(file_path):
    audio = AudioSegment.from_file(file_path)
    duration_seconds = len(audio) / 1000  # Convert milliseconds to seconds
    return int(duration_seconds)  # Return total seconds as an integer

# Utility Functions
def read_json(file_path: str):
    """Reads JSON data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return []

def extract_transcripts(json_data, speaker_type):
    """Extracts transcripts for the specified speaker type."""
    return " ".join(
        row.get('actual_transcript', '').strip().lower()
        for row in json_data if row.get('speaker_id', '').lower() == speaker_type
    )

def calculate_word_frequencies(text):
    """Calculates the top 5 word frequencies, excluding stop words."""
    word_freq = {}
    for word in text.lower().split():
        if word not in STOP_WORDS:
            word_freq[word] = word_freq.get(word, 0) + 1
    return sorted(
        [{"word": word, "frequency": freq} for word, freq in word_freq.items()],
        key=lambda x: x["frequency"], reverse=True
    )[:5]

def check_keywords(transcript, tags):
    """Checks for the presence of specific keywords in the transcript."""
    return {tag: 'yes' if tag in transcript else 'no' for tag in tags}

def process_transcript(transcript, confidence_score, speaker_id, start_time, end_time, sentiment, sentiment_score):
    """Processes the transcript and returns word-level data."""
    words = transcript.split()
    word_duration = (end_time - start_time) / max(len(words), 1)
    return [
        {
            "word": word,
            "start": start_time + i * word_duration,
            "end": start_time + (i + 1) * word_duration,
            "confidence": confidence_score,
            "speaker": speaker_id,
            "speaker_confidence": confidence_score,
            "punctuated_word": word.capitalize() if word.isalpha() else word,
            "sentiment": sentiment,
            "sentiment_score": sentiment_score
        }
        for i, word in enumerate(words)
    ]

def combine_data(confidence_data, sentiment_data=None):
    """Combines confidence data with optional sentiment data."""
    combined_data, overall_transcript_words = [], []

    for conf_entry in confidence_data:
        start, end = float(conf_entry['start_time']), float(conf_entry['end_time'])
        
        # Default dummy values for sentiment
        sentiment_label = 'neutral'
        sentiment_score = 0.0
        
        # If sentiment data is provided, match it
        if sentiment_data:
            matched_sentiments = [
                sent for sent in sentiment_data
                if start >= float(sent['start_time']) and end <= float(sent['end_time'])
            ]
            if matched_sentiments:
                sentiment_label = matched_sentiments[0]['emotion_label']
                sentiment_score = matched_sentiments[0]['sentiment_confidence_score']
        
        word_data = process_transcript(
            conf_entry['transcription'], conf_entry['transcription_confidence_score'],
            conf_entry['speaker_id'], start, end, sentiment_label, sentiment_score
        )
        overall_transcript_words.extend(word_data)
        combined_data.append({
            'start': start, 'end': end, 'channel': 0,
            'speaker': conf_entry['speaker_id'], 'confidence': conf_entry['transcription_confidence_score'],
            'sentiment': sentiment_label, 'sentiment_score': sentiment_score,
            'transcript': conf_entry['transcription'], 'words': word_data, 'id': str(uuid.uuid4())
        })
    
    return combined_data, overall_transcript_words

def get_transcripts_with_confidence(json_file_path):
    """Extracts transcripts along with confidence scores."""
    json_data = read_json(json_file_path)
    return [
        {
            "transcription": item.get("transcription", "").strip(),
            "transcription_confidence_score": item.get("transcription_confidence_score", 0.0),
            "start_time": item.get("start_time", ""),
            "end_time": item.get("end_time", ""),
            "speaker_id": item.get("speaker_id", "")
        } for item in json_data
    ]

def get_all_transcriptions(json_file_path):
    """Concatenates all transcriptions."""
    return " ".join(
        item.get("transcription", "").strip() for item in read_json(json_file_path)
    ).strip()

# Agent and Customer Transcript Extraction
def extract_agent_transcripts(json_file_path):
    """Extracts all agent transcripts."""
    return extract_transcripts(read_json(json_file_path), 'agent')

def extract_customer_transcripts(json_file_path):
    """Extracts all customer transcripts."""
    return extract_transcripts(read_json(json_file_path), 'customer')


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
