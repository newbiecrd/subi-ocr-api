from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import requests, fitz, io

app = FastAPI(title="Subi OCR API", version="2.0")

# 🧩 1. Nhận nhiều ảnh, gộp thành 1 PDF
def merge_images_to_pdf(files):
    pdf = fitz.open()
    for f in files:
        image_data = f.file.read()
        img = fitz.open(stream=image_data, filetype=f.content_type.split('/')[-1])
        rect = img[0].rect
        pdf_bytes = io.BytesIO()
        page = pdf.new_page(width=rect.width, height=rect.height)
        page.show_pdf_page(rect, img, 0)
    output = io.BytesIO()
    pdf.save(output)
    pdf.close()
    output.seek(0)
    return output

# 🧩 2. Endpoint nhận nhiều ảnh
@app.post("/ocrMulti")
async def ocr_multi(files: list[UploadFile] = File(...)):
    try:
        pdf_data = merge_images_to_pdf(files)

        # gửi PDF qua Google Apps Script để OCR
        apps_script_url = "https://script.google.com/macros/s/AKfycbworDCQI5JQKjhuLyGhG3rOs85V8h8dBgy5MK4D0bz16zhTwu9CyLDoxCGE1JLn8lk/exec"
        res = requests.post(apps_script_url, files={"file": ("merged.pdf", pdf_data, "application/pdf")}, timeout=120)

        if res.status_code == 200:
            return JSONResponse(content={"ok": True, "source": "Render→AppsScript", "data": res.json()})
        else:
            return JSONResponse(content={"ok": False, "error": f"Google Apps Script error {res.status_code}", "text": res.text})

    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)})
