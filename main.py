from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os, shutil
from fastapi.responses import FileResponse
import zipfile


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

os.makedirs("recordings", exist_ok=True)

@app.post("/upload")
async def upload(file: UploadFile, sentence: str = Form(...), index: int = Form(...)):
    filename = f"{index:04}.wav"
    filepath = os.path.join("recordings", filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with open("recordings/metadata.csv", "a", encoding="utf-8") as f:
        f.write(f"{filename}|{sentence.strip()}|{sentence.strip()}\n")

    return {"status": "ok"}


@app.get("/download")
def download_recordings():
    zip_path = "recordings.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for fname in os.listdir("recordings"):
            if fname.endswith(".wav") or fname.endswith(".csv"):
                zipf.write(os.path.join("recordings", fname), arcname=fname)
    return FileResponse(zip_path, filename="recordings.zip")


@app.get("/sentences")
async def get_sentences():
    sentence_list = []
    with open("static/sentences.txt", "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                index, sentence = line.strip().split("|", 1)
                sentence_list.append({"index": int(index), "text": sentence})
    return JSONResponse(sentence_list)

@app.get("/")
async def main():
    with open("static/index.html", "r") as f:
        return HTMLResponse(f.read())
