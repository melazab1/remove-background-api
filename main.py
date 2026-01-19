from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response
import subprocess
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "API is running"}

@app.post("/remove-background")
async def remove_background(file: UploadFile = File(...)):
    input_path = "temp_input.png"
    output_path = "temp_output.png"
    
    with open(input_path, "wb") as f:
        f.write(await file.read())
    
    subprocess.run(["convert", input_path, "-fuzz", "10%", "-transparent", "white", output_path])
    
    with open(output_path, "rb") as f:
        result = f.read()
    
    os.remove(input_path)
    os.remove(output_path)
    
    return Response(content=result, media_type="image/png")

