from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
import subprocess
import os
import uuid
from asyncio import Semaphore
import httpx
from typing import Optional

app = FastAPI()
semaphore = Semaphore(5)

@app.get("/")
def read_root():
    return {"status": "API is running"}

async def process_and_callback(file_content: bytes, job_id: str, webhook_url: str):
    async with semaphore:
        input_path = f"temp_input_{job_id}.png"
        output_path = f"temp_output_{job_id}.png"
        
        try:
            with open(input_path, "wb") as f:
                f.write(file_content)
            
            subprocess.run(["convert", input_path, "-fuzz", "10%", "-transparent", "white", output_path])
            
            with open(output_path, "rb") as f:
                result_bytes = f.read()
            
            # إرسال النتيجة للـ webhook
            async with httpx.AsyncClient(timeout=30.0) as client:
                files = {"file": (f"{job_id}.png", result_bytes, "image/png")}
                await client.post(webhook_url, files=files, data={"job_id": job_id, "status": "completed"})
        
        except Exception as e:
            # إرسال خطأ للـ webhook
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(webhook_url, json={"job_id": job_id, "status": "failed", "error": str(e)})
        
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)

@app.post("/remove-background")
async def remove_background(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    webhook_url: Optional[str] = None
):
    job_id = str(uuid.uuid4())
    file_content = await file.read()
    
    if webhook_url:
        # معالجة async مع webhook
        background_tasks.add_task(process_and_callback, file_content, job_id, webhook_url)
        return JSONResponse({"job_id": job_id, "status": "processing", "message": "Will send result to webhook"})
    else:
        return JSONResponse({"error": "webhook_url is required"}, status_code=400)
