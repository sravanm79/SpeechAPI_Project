import os
import shutil

import numpy as np
import scipy.io.wavfile
from pydub import AudioSegment, effects
from pydub.silence import split_on_silence

from single_file_inference import start_all, parse_transcription

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def split_audio_chunks(rttm_data, wav_path, output_dir="audio_chunks"):
    start_times, end_times, spk_id = parse_rttm_data(rttm_data)
    fs1, y1 = scipy.io.wavfile.read(wav_path)

    start_times = np.ceil(start_times * fs1)
    end_times = np.ceil(end_times * fs1)

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.mkdir(output_dir)

    for i in range(start_times.shape[0]):
        start_read = int(start_times[i])
        end_read = int(end_times[i])

        if start_read >= y1.shape[0]:
            start_read = y1.shape[0] - 1
        if end_read >= y1.shape[0]:
            end_read = y1.shape[0] - 1

        segment_path = os.path.join(output_dir, "{num}_{id}.wav".format(num=i + 1, id=spk_id[i]))
        scipy.io.wavfile.write(segment_path, fs1, np.array(y1[start_read:end_read]))


def parse_rttm_data(rttm_data):
    start_times = []
    end_times = []
    spk_id = []

    lines = rttm_data.split("\n")
    for line in lines:
        parts = line.split(" ")
        if len(parts) < 7:
            break
        start_times.append(float(parts[3]))
        end_times.append(start_times[-1] + float(parts[4]))
        spk_id.append(parts[7][-2:])
        # Round the time values to 3rd decimals $ask devash
    start_times = np.array(start_times).round(decimals=3)
    end_times = np.array(end_times).round(decimals=3)

    return start_times, end_times, spk_id


def getConversationFormatFromWav(wav_path, rttm_data, language):
    act_id = {}
    temp_output_dir = "temp_output_dir"
    split_audio_chunks(rttm_data, wav_path, temp_output_dir)

    # Process the RTTM file and organize the results in a conversation format
    start_times, end_times, spk_id = parse_rttm_data(rttm_data)
    end_max = end_times[0]
    conversation_format = []
    substring_list = ["morning", "urban", "company", "good", "evening", "afternoon", "calling"]
    # if start_times[0] > 1:
    #     start_time = str(0)
    #     end_time = str(start_times[0])
    #     speaker_id = " "
    #     transcription = "Silence"
    for i in range(len(start_times)):
        start_time = start_times[i]
        end_time = end_times[i]
        speaker_id = spk_id[i]
        # Load the segment WAV file
        segment_wav_path = os.path.join(temp_output_dir, f"{i + 1}_{speaker_id}.wav")
        try:
            transcription, conf_score = predict_transcription(segment_wav_path)
        except:
            transcription = "entry"
            conf_score = 1.3
            pass
        #print(transcription)

        if act_id == {} and any(substring in transcription for substring in substring_list):
            if str(spk_id[i]) == "00":
                act_id["00"] = "Agent"
                act_id["0"] = "Agent"
                act_id["01"] = "Customer"
                act_id["1"] = "Customer"
            elif str(spk_id[i]) == "01":
                act_id["01"] = "Agent"
                act_id["1"] = "Agent"
                act_id["00"] = "Customer"
                act_id["0"] = "Customer"
        if end_times[i] - start_times[i] > 0.25 or transcription != " ":
            start_time = str(start_times[i])
            end_time = str(end_times[i])
            speaker_id = str(spk_id[i])
            transcription = transcription
        if end_times[i] > end_max:
            end_max = end_times[i]

        # Organize the results in the conversation format
        conversation_format.append({
            "start_time": start_time,
            "end_time": end_time,
            "speaker_id": speaker_id,
            "act_id": speaker_id,
            "transcription": transcription,
            "actual_transcript": transcription,
            "language": language,
            "actual_language": "english",
            "transcription_confidence_score":conf_score
        })

    # Remove temporary directory
    shutil.rmtree(temp_output_dir)

    return conversation_format, act_id


def predict_transcription(segment_wav_path):
    audio_file = AudioSegment.from_file(segment_wav_path, format="wav")
    audio_file = audio_file.set_channels(1)
    audio_file = audio_file.set_frame_rate(16000)
    # Normalizing the audio file
    # import noisereduce
    # audio_file=noisereduce.reduce_noise(np.array(audio_file.get_array_of_samples()),16000)
    # from scipy.io import wavfile
    # wavfile.write("temp.wav",rate=16000,data=audio_file)
    # audio_file = AudioSegment.from_file("temp.wav",format="wav")
    # os.remove("temp.wav")
    audio_file = effects.normalize(audio_file)
    # duration=get_duration(audio_file)
    if os.path.exists("chunked"):
        shutil.rmtree("chunked")
    # Create temp folder chunked to store data
    os.mkdir("chunked")
    transcription = ""
    # Chunk the file and create small transcription of each chunk
    audio_chunks = split_on_silence(audio_file, min_silence_len=800, silence_thresh=-40, keep_silence=500)
    for chunkIndex, subChunk in enumerate(audio_chunks):
        out_file = "chunked/chunk{}.wav".format(chunkIndex)
        subChunk.export(out_file, format="wav")
        wav_path = out_file
        transcript,conf_score = parse_transcription(wav_path=wav_path, lang='en')
        transcription += " " + transcript
        
    shutil.rmtree("chunked")
    return transcription,conf_score

