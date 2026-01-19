from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import Response
import subprocess
import os
import uuid
from asyncio import Semaphore

app = FastAPI()

# تحديد عدد المعالجات المتزامنة (5 في نفس الوقت)
semaphore = Semaphore(5)

@app.get("/")
def read_root():
    return {"status": "API is running"}

async def process_image(file_content: bytes) -> bytes:
    async with semaphore:
        # إنشاء اسم فريد لكل ملف
        unique_id = str(uuid.uuid4())
        input_path = f"temp_input_{unique_id}.png"
        output_path = f"temp_output_{unique_id}.png"
        
        try:
            with open(input_path, "wb") as f:
                f.write(file_content)
            
            subprocess.run(["convert", input_path, "-fuzz", "10%", "-transparent", "white", output_path])
            
            with open(output_path, "rb") as f:
                result = f.read()
            
            return result
        finally:
            # تنظيف الملفات
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)

@app.post("/remove-background")
async def remove_background(file: UploadFile = File(...)):
    file_content = await file.read()
    result = await process_image(file_content)
    return Response(content=result, media_type="image/png")
