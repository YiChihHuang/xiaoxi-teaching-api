"""
小汐旁門左道 — Teaching Monster API (Minimal)
NotebookLM 影片回傳用的簡易 API
"""
import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xiaoxi-api")

app = FastAPI(title="小汐旁門左道 API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

PORT = int(os.environ.get("PORT", 8000))
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", os.environ.get("BASE_URL", "https://xiaoxi-teaching-api.onrender.com"))

class GenerateRequest(BaseModel):
    request_id: str
    course_requirement: str
    student_persona: str = ""

class GenerateResponse(BaseModel):
    video_url: str
    subtitle_url: str = ""
    supplementary_url: list = []

def find_video(request_id: str):
    d = OUTPUT_DIR / request_id
    if not d.exists():
        return None
    mp4s = list(d.glob("*.mp4"))
    return mp4s[0] if mp4s else None

# === Main endpoint: platform calls this ===
@app.post("/generate")
@app.post("/")
async def generate(req: GenerateRequest):
    logger.info(f"📥 request_id={req.request_id}, course={req.course_requirement[:80]}")
    
    video = find_video(req.request_id)
    if video:
        base = BASE_URL.rstrip("/")
        logger.info(f"🎬 Found pre-uploaded video: {video}")
        return GenerateResponse(
            video_url=f"{base}/videos/{req.request_id}",
            subtitle_url="",
            supplementary_url=[],
        )
    
    raise HTTPException(status_code=404, detail=f"No video found for {req.request_id}. Upload first via POST /upload/{{request_id}}")

# === Upload video ===
@app.post("/upload/{request_id}")
async def upload(request_id: str, file: UploadFile = File(...)):
    d = OUTPUT_DIR / request_id
    d.mkdir(parents=True, exist_ok=True)
    dest = d / f"{request_id}.mp4"
    content = await file.read()
    dest.write_bytes(content)
    logger.info(f"📤 Uploaded: {dest} ({len(content)} bytes)")
    return {"status": "ok", "path": str(dest), "size": len(content)}

# === Download video ===
@app.get("/videos/{request_id}")
async def download_video(request_id: str):
    video = find_video(request_id)
    if not video:
        raise HTTPException(404, f"No video for {request_id}")
    return FileResponse(video, media_type="video/mp4", filename=f"{request_id}.mp4")

# === Status ===
@app.get("/status")
async def status():
    videos = list(OUTPUT_DIR.glob("*/*.mp4"))
    return {"status": "ok", "videos_count": len(videos), "base_url": BASE_URL}

@app.get("/")
async def root():
    return {"service": "小汐旁門左道 Teaching Monster API", "version": "1.0", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
