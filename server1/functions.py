import os
import json
import uuid
import hashlib
import subprocess
import requests
import audioread
from pydub import AudioSegment
from flask import Flask
from logging_setup import logger_level

# Logging Configuration
logger_info = logger_level("INFO", filename=os.path.basename(__file__))
logger_debug = logger_level("DEBUG", filename=os.path.basename(__file__))
logger_error = logger_level("ERROR", filename=os.path.basename(__file__))
logger_warning = logger_level("WARNING", filename=os.path.basename(__file__))
logger_critical = logger_level("CRITICAL", filename=os.path.basename(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


class AudioConverter:
    """
    A utility class for converting audio files to WAV format using FFmpeg or SoX.
    """

    @staticmethod
    def run_ffmpeg_conversion(input_path, output_path):
        ffmpeg_cmd = ["ffmpeg", "-y", "-i", input_path, output_path]
        result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            logger_info.info(f"File converted to WAV using FFmpeg: {output_path}")
            return True
        logger_error.error(f"FFmpeg conversion failed: {result.stderr.decode()}")
        return False

    @staticmethod
    def run_sox_conversion(input_path, output_path):
        sox_cmd = ["sox", input_path, output_path]
        result = subprocess.run(sox_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            logger_info.info(f"File converted to WAV using SoX: {output_path}")
            return True
        logger_error.error(f"SoX conversion failed: {result.stderr.decode()}")
        return False

class AudioUtils:
    """Utility class for audio file processing."""
    
    @staticmethod
    def get_audio_duration(file_path):
        """Calculate the duration of the audio file in seconds."""
        audio = AudioSegment.from_file(file_path)
        return int(len(audio) / 1000)
    
    @staticmethod
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
            if response.status_code != 200:
                logger_error.error(f"Failed to download audio. Status code: {response.status_code}")
                return None

            with open(original_file_path, 'wb') as audio_file:
                for chunk in response.iter_content(chunk_size=8192):
                    audio_file.write(chunk)

            logger_info.info(f"File downloaded successfully: {original_file_path}")

            # Ensure file exists and is not empty
            if not os.path.exists(original_file_path) or os.path.getsize(original_file_path) == 0:
                logger_error.error(f"Downloaded file is missing or empty: {original_file_path}")
                return None

            # If the file is already WAV, return it
            if original_file_path.lower().endswith('.wav'):
                logger_info.info(f"File is already in WAV format: {original_file_path}")
                return original_file_path

            wav_file_path = os.path.join(output_directory, f"{os.path.splitext(sanitized_file_name)[0]}.wav")
            logger_debug.debug(f"Attempting to convert file to WAV: {wav_file_path}")

            # Detect format using audioread
            detected_format = None
            try:
                with audioread.audio_open(original_file_path) as f:
                    detected_format = f.format
                logger_info.info(f"Detected format: {detected_format}")
            except Exception as e:
                logger_warning.warning(f"Could not detect format with audioread: {e}")

            # Convert using pydub (FFmpeg)
            try:
                audio = AudioSegment.from_file(original_file_path, format=detected_format)
                audio.export(wav_file_path, format="wav")
                logger_info.info(f"File converted to WAV using pydub: {wav_file_path}")
            except Exception as e:
                logger_error.error(f"pydub failed: {e}. Trying FFmpeg.")

                # Fallback to FFmpeg CLI
                if not AudioConverter.run_ffmpeg_conversion(original_file_path, wav_file_path):
                    logger_warning.warning("FFmpeg failed. Trying SoX.")

                    # Final fallback to SoX
                    if not AudioConverter.run_sox_conversion(original_file_path, wav_file_path):
                        raise RuntimeError("All conversion methods failed.")

            logger_info.info(f"Returning WAV file path: {wav_file_path}")
            return wav_file_path

        except requests.exceptions.RequestException as req_err:
            logger_error.error(f"Error during file download: {str(req_err)}")
            raise RuntimeError(f"Error during file download: {str(req_err)}")
        except Exception as e:
            logger_error.error(f"Error during download or conversion: {str(e)}")
            raise RuntimeError(f"Error during download or conversion: {str(e)}")




class JSONUtils:
    """Utility class for JSON file handling."""
    
    @staticmethod
    def read_json(file_path):
        """Reads JSON data from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            logger_error.error(f"Error reading JSON file: {e}")
            return []

class TranscriptProcessor:
    """Class to handle transcript processing and analysis."""
    
    STOP_WORDS = {"i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "you're", "you've", "you'll", "you'd"}
    
    @staticmethod
    def extract_transcripts(json_data, speaker_type):
        """Extracts transcripts for the specified speaker type."""
        return " ".join(row.get('actual_transcript', '').strip().lower() for row in json_data if row.get('speaker_id', '').lower() == speaker_type)
    
    @staticmethod
    def calculate_word_frequencies(text):
        """Calculates word frequencies, excluding stop words."""
        word_freq = {}
        for word in text.lower().split():
            if word not in TranscriptProcessor.STOP_WORDS:
                word_freq[word] = word_freq.get(word, 0) + 1
        return sorted([{"word": word, "frequency": freq} for word, freq in word_freq.items()], key=lambda x: x["frequency"], reverse=True)[:5]
    
    @staticmethod
    def check_keywords(transcript, tags):
        """Checks for specific keywords in the transcript."""
        return {tag: 'yes' if tag in transcript else 'no' for tag in tags}

class SentimentProcessor:
    """Class to handle sentiment and confidence data processing."""
    
    @staticmethod
    def process_transcript(transcript, confidence_score, speaker_id, start_time, end_time, sentiment, sentiment_score):
        """Processes the transcript and returns word-level data."""
        words = transcript.split()
        word_duration = (end_time - start_time) / max(len(words), 1)
        return [{
            "word": word,
            "start": start_time + i * word_duration,
            "end": start_time + (i + 1) * word_duration,
            "confidence": confidence_score,
            "speaker": speaker_id,
            "speaker_confidence": confidence_score,
            "punctuated_word": word.capitalize() if word.isalpha() else word,
            "sentiment": sentiment,
            "sentiment_score": sentiment_score
        } for i, word in enumerate(words)]
    
    @staticmethod
    def combine_data(confidence_data, sentiment_data=None):
        """Combines confidence data with optional sentiment data."""
        combined_data, overall_transcript_words = [], []
        for conf_entry in confidence_data:
            start, end = float(conf_entry['start_time']), float(conf_entry['end_time'])
            sentiment_label = 'neutral'
            sentiment_score = 0.0
            if sentiment_data:
                matched_sentiments = [sent for sent in sentiment_data if start >= float(sent['start_time']) and end <= float(sent['end_time'])]
                if matched_sentiments:
                    sentiment_label = matched_sentiments[0]['emotion_label']
                    sentiment_score = matched_sentiments[0]['sentiment_confidence_score']
            word_data = SentimentProcessor.process_transcript(conf_entry['transcription'], conf_entry['transcription_confidence_score'], conf_entry['speaker_id'], start, end, sentiment_label, sentiment_score)
            overall_transcript_words.extend(word_data)
            combined_data.append({
                'start': start, 'end': end, 'speaker': conf_entry['speaker_id'], 'confidence': conf_entry['transcription_confidence_score'], 'sentiment': sentiment_label, 'sentiment_score': sentiment_score, 'transcript': conf_entry['transcription'], 'words': word_data, 'id': str(uuid.uuid4())
            })
        return combined_data, overall_transcript_words


class TranscriptHandler:
    """
    A class for processing transcripts from JSON files.
    """

    @staticmethod
    def get_transcripts_with_confidence(json_file_path):
        """Extracts transcripts along with confidence scores."""
        json_data = JSONUtils.read_json(json_file_path)
        return [
            {
                "transcription": item.get("transcription", "").strip(),
                "transcription_confidence_score": item.get("transcription_confidence_score", 0.0),
                "start_time": item.get("start_time", ""),
                "end_time": item.get("end_time", ""),
                "speaker_id": item.get("speaker_id", "")
            } for item in json_data
        ]

    @staticmethod
    def get_all_transcriptions(json_file_path):
        """Concatenates all transcriptions."""
        return " ".join(
            item.get("transcription", "").strip() for item in JSONUtils.read_json(json_file_path)
        ).strip()

    @staticmethod
    def extract_agent_transcripts(json_file_path):
        """Extracts all agent transcripts."""
        return TranscriptProcessor.extract_transcripts(JSONUtils.read_json(json_file_path), 'agent')

    @staticmethod
    def extract_customer_transcripts(json_file_path):
        """Extracts all customer transcripts."""
        return TranscriptProcessor.extract_transcripts(JSONUtils.read_json(json_file_path), 'customer')

class FileHandler:
    """
    A utility class for handling file-related operations such as validation, 
    saving, and format conversion.
    """

    @staticmethod
    def validate_file_size(uploaded_file, max_size):
        uploaded_file.seek(0, os.SEEK_END)
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)
        return file_size <= max_size

    @staticmethod
    def save_uploaded_file(uploaded_file):
        file_path = os.path.join(PROJECT_ROOT, "uploads", uploaded_file.filename)
        uploaded_file.save(file_path)
        return file_path

    @staticmethod
    def validate_audio_format(file_path):
        return os.path.splitext(file_path)[1].lower() in {'.mp3', '.wav'}

    @staticmethod
    def convert_to_wav_if_needed(file_path):
        if file_path.lower().endswith('.mp3'):
            logger_debug.debug("Converting MP3 to WAV format.")
            sound = AudioSegment.from_mp3(file_path)
            new_file_path = file_path.replace(".mp3", ".wav")
            sound.export(new_file_path, format="wav")
            logger_info.info(f"Conversion completed successfully: {new_file_path}")
            return new_file_path
        return file_path

