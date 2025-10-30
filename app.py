from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import tempfile, requests, os

APPS_SCRIPT_URL = os.getenv(
    "APPS_SCRIPT_URL",
    "https://script.google.com/macros/s/AKfycbworDCQI5JQKjhuLyGhG3rOs85V8h8dBgy5MK4D0bz16zhTwu9CyLDoxCGE1JLn8lk/exec"
)
API_KEY = os.getenv("SUBI_API_KEY", "SUBI-12345")

app = FastAPI(title="Subi OCR API", version="1.0")

# --- OCR giả lập (sẽ thay bằng olmOCR thật sau) ---
def ocr_to_text(file_path: str) -> str:
    return "Giấy chứng nhận CN 123456, địa chỉ 75 Tô Hiệu, Phú Thọ Hoà, diện tích 62,4 m²."

@app.post("/ocr")
async def ocr_and_fill(file: UploadFile = File(...), mode: str = "ocrText"):
    suffix = os.path.splitext(file.filename or "")[1] or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        text_output = ocr_to_text(tmp_path)

        if mode == "ocrText":
            payload = {"ocrText": text_output}
        else:
            payload = {
                "placeholders": {"04":"Nguyễn Văn A","20.1":"CN 123456"},
                "options": {}
            }

        headers = {"x-api-key": API_KEY}
        resp = requests.post(APPS_SCRIPT_URL, json=payload, headers=headers, timeout=120)

        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        return JSONResponse({"ok": True, "apps_script_response": data})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
