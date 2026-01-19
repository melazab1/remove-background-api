from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import subprocess
import os
import uuid
from asyncio import Semaphore
import asyncio
from pathlib import Path

app = FastAPI()
semaphore = Semaphore(5)

# مجلد النتائج
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

async def delete_after_delay(job_id: str):
    """حذف الملفات بعد 5 دقائق"""
    await asyncio.sleep(300)  # 5 دقائق
    status_file = RESULTS_DIR / f"{job_id}.json"
    result_file = RESULTS_DIR / f"{job_id}.png"
    
    if status_file.exists():
        os.remove(status_file)
    if result_file.exists():
        os.remove(result_file)

async def process_image(job_id: str, file_content: bytes):
    async with semaphore:
        input_path = f"temp_input_{job_id}.png"
        output_path = RESULTS_DIR / f"{job_id}.png"
        status_file = RESULTS_DIR / f"{job_id}.json"
        
        try:
            # تحديث الحالة: processing
            with open(status_file, "w") as f:
                f.write('{"status":"processing"}')
            
            with open(input_path, "wb") as f:
                f.write(file_content)
            
            subprocess.run(["convert", input_path, "-fuzz", "10%", "-transparent", "white", str(output_path)])
            
            # تحديث الحالة: completed
            with open(status_file, "w") as f:
                f.write('{"status":"completed"}')
        
        except Exception as e:
            with open(status_file, "w") as f:
                f.write(f'{{"status":"failed","error":"{str(e)}"}}')
        
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)

@app.get("/")
def read_root():
    return {"status": "API is running"}

@app.post("/remove-background")
async def remove_background(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    file_content = await file.read()
    
    # إنشاء ملف الحالة
    status_file = RESULTS_DIR / f"{job_id}.json"
    with open(status_file, "w") as f:
        f.write('{"status":"queued"}')
    
    background_tasks.add_task(process_image, job_id, file_content)
    background_tasks.add_task(delete_after_delay, job_id)
    
    return JSONResponse({"job_id": job_id, "status": "queued"})

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    status_file = RESULTS_DIR / f"{job_id}.json"
    result_file = RESULTS_DIR / f"{job_id}.png"
    
    if not status_file.exists():
        return JSONResponse({"error": "Job not found"}, status_code=404)
    
    with open(status_file, "r") as f:
        status = f.read()
    
    if "completed" in status and result_file.exists():
        return FileResponse(result_file, media_type="image/png")
    else:
        return JSONResponse({"status": status}, status_code=202)
