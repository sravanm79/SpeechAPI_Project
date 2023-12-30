from fastapi import FastAPI, UploadFile, HTTPException
from pynnote_diarization import diarize_audio

app = FastAPI()

@app.post("/diarize")
async def diarize_file(file: UploadFile = File(...)):
    # Diarize audio using Pynnote
    result = diarize_audio(file)

    return result
