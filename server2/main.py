import os
import shutil
import scipy.io.wavfile
import numpy as np
import subprocess

from single_file_inference import get_results, start_all, parse_transcription, Wav2VecCtc


def split_audio_chunks(rttm_path, wav_path, output_dir="audio_chunks"):
    start_times, end_times, spk_id = read_rttm_file(rttm_path)
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


def read_rttm_file(rttm_path):
    start_times = []
    end_times = []
    spk_id = []

    with open(rttm_path, 'r') as f:
        while True:
            line = f.readline()
            lines = line.split(" ")
            if len(lines) < 7:
                break
            start_times.append(float(lines[3]))
            end_times.append(start_times[-1] + float(lines[4]))
            spk_id.append(lines[7])

    return np.array(start_times), np.array(end_times), spk_id


def getConversationFormatFromWav(wav_path, rttm_file):
    temp_output_dir = "temp_output_dir"
    split_audio_chunks(rttm_file, wav_path, temp_output_dir)

    # Process the RTTM file and organize the results in a conversation format
    start_times, end_times, spk_id = read_rttm_file(rttm_file)

    conversation_format = []

    for i in range(len(start_times)):
        start_time = start_times[i]
        end_time = end_times[i]
        speaker_id = spk_id[i]

        # Load the segment WAV file
        segment_wav_path = os.path.join(temp_output_dir, f"{i + 1}_{speaker_id}.wav")
        transcription = parse_transcription(segment_wav_path, "en")

        # Organize the results in the conversation format
        conversation_format.append({
            "start_time": start_time,
            "end_time": end_time,
            "speaker_id": speaker_id,
            "transcription": transcription,
            "language": "english"
        })

    # Remove temporary directory
    shutil.rmtree(temp_output_dir)

    return conversation_format


def run_pyanote_bash_script(script_path):
    try:
        # Run the bash script
        process = subprocess.Popen(["bash", script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Wait for the script to finish
        stdout, stderr = process.communicate()

        # Check the return code
        return_code = process.returncode
        if return_code == 0:
            print("Script execution successful.")
            print("Stdout:", stdout.decode())
        else:
            print("Script execution failed with return code:", return_code)
            print("Stdout:", stdout.decode())
            print("Stderr:", stderr.decode())

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    bash_script_path = './pyanote.sh'
    input_wav_path = "/tmp/pycharm_project_701/english.wav"
    wav_file = "./temp.wav"

    shutil.copy(input_wav_path, wav_file)

    run_pyanote_bash_script(bash_script_path)
    base_path = os.getcwd()
    start_all(base_path)
    print("started")
    conversation_format = getConversationFormatFromWav('english.wav', 'english.rttm')
