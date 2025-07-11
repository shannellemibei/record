from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os, shutil, zipfile, subprocess

app = FastAPI()

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Ensure directories exist
os.makedirs("recordings", exist_ok=True)
os.makedirs("recordings/webm", exist_ok=True)

@app.post("/upload")
async def upload(file: UploadFile, sentence: str = Form(...), index: int = Form(...)):
    # File names
    webm_filename = f"{index:04}.webm"
    wav_filename = f"{index:04}.wav"

    webm_path = os.path.join("recordings/webm", webm_filename)
    wav_path = os.path.join("recordings", wav_filename)

    # Save .webm file in subfolder
    with open(webm_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Convert to .wav using ffmpeg
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", webm_path, wav_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        return {"status": "error", "message": f"ffmpeg conversion failed: {e}"}

    # Write metadata
    with open("recordings/metadata.csv", "a", encoding="utf-8") as f:
        f.write(f"{wav_filename}|{sentence.strip()}|{sentence.strip()}\n")

    return {"status": "ok"}

@app.get("/download")
def download_recordings():
    zip_path = "recordings.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        # Add wav and csv
        for fname in os.listdir("recordings"):
            fpath = os.path.join("recordings", fname)
            if os.path.isfile(fpath) and (fname.endswith(".wav") or fname.endswith(".csv")):
                zipf.write(fpath, arcname=fname)

        # Add webm subfolder contents
        webm_dir = "recordings/webm"
        for fname in os.listdir(webm_dir):
            fpath = os.path.join(webm_dir, fname)
            if os.path.isfile(fpath):
                zipf.write(fpath, arcname=os.path.join("webm", fname))

    return FileResponse(zip_path, filename="recordings.zip", media_type='application/zip')

@app.get("/sentences")
async def get_sentences():
    sentence_list = []
    with open("static/sentences.txt", "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                index, sentence = line.strip().split("|", 1)
                sentence_list.append({"index": int(index), "text": sentence})
    return JSONResponse(sentence_list)

@app.post("/upload/manual")
async def manual_upload(file: UploadFile, sentence: str = Form(...)):
    # Find next available index
    existing = [f for f in os.listdir("recordings") if f.endswith(".wav")]
    indices = [int(f.split(".")[0]) for f in existing if f.split(".")[0].isdigit()]
    next_index = max(indices, default=0) + 1

    webm_filename = f"{next_index:04}.webm"
    wav_filename = f"{next_index:04}.wav"

    webm_path = os.path.join("recordings/webm", webm_filename)
    wav_path = os.path.join("recordings", wav_filename)

    # Save the uploaded audio
    with open(webm_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Convert to .wav
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", webm_path, wav_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        return {"status": "error", "message": f"ffmpeg conversion failed: {e}"}

    # Save to metadata
    with open("recordings/metadata.csv", "a", encoding="utf-8") as f:
        f.write(f"{wav_filename}|{sentence.strip()}|{sentence.strip()}\n")

    return {"status": "ok", "index": next_index}


@app.get("/")
async def main():
    with open("static/index.html", "r") as f:
        return HTMLResponse(f.read())
