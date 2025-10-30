# ================================
# app.py — Subi OCR (auto PDF merge + placeholder JSON)
# Version: 1.1 — for Render deploy
# ================================

import io, os, base64, tempfile
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from PIL import Image
import fitz  # PyMuPDF
import pytesseract

app = FastAPI(title="Subi OCR API", version="1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================
# UTILS
# =============================

def merge_images_to_pdf(image_files: List[UploadFile]) -> bytes:
    """Gộp nhiều ảnh thành 1 file PDF (Pillow)."""
    images = []
    for f in image_files:
        img = Image.open(io.BytesIO(f.file.read())).convert("RGB")
        images.append(img)
    buf = io.BytesIO()
    images[0].save(buf, save_all=True, append_images=images[1:], format="PDF")
    return buf.getvalue()


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """OCR từng trang PDF (PyMuPDF + pytesseract)."""
    text_all = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, lang="vie")
            text_all.append(text.strip())
    return "\n\n----\n\n".join(text_all)


def simple_extract_placeholders(text: str) -> dict:
    """Demo trích xuất sơ bộ placeholder từ text OCR."""
    result = {}

    # Họ tên (04)
    import re
    m_name = re.search(r"Họ\s*tên\s*[:\-]?\s*([A-ZÀ-ỸĐ][A-ZÀ-ỸĐ\s]+)", text, re.I)
    if m_name:
        result["04"] = m_name.group(1).strip().title()

    # Ngày sinh (05)
    m_dob = re.search(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})", text)
    if m_dob:
        result["05"] = m_dob.group(1)

    # Số GCN (20.1)
    m_gcn = re.search(r"\b(CN|CV|CS)\s*\d{3,}\b", text)
    if m_gcn:
        result["20.1"] = m_gcn.group(0).replace(" ", "")

    # Diện tích (20.5)
    m_dt = re.search(r"Diện\s*tích[^:]*[:\-]?\s*([\d\.,]+)\s*m", text)
    if m_dt:
        result["20.5"] = m_dt.group(1).replace(",", ".") + " m²"

    # Nguồn gốc (41.9)
    if "chuyển nhượng" in text.lower():
        result["41.9"] = "Nhận chuyển nhượng"
    elif "tặng cho" in text.lower():
        result["41.9"] = "Tặng cho"
    elif "thừa kế" in text.lower():
        result["41.9"] = "Thừa kế"

    return result


# =============================
# ROUTES
# =============================

@app.get("/")
def root():
    return {"message": "Subi OCR API is running", "version": "1.1"}


@app.get("/ping")
def ping():
    return {"ok": True, "message": "pong"}


@app.post("/ocrAndFill")
async def ocr_and_fill(
    file: List[UploadFile] = File(...),
    mode: Optional[str] = Form("placeholders")
):
    try:
        # Gộp PDF nếu nhiều ảnh
        if len(file) > 1:
            pdf_bytes = merge_images_to_pdf(file)
        else:
            f0 = file[0]
            if f0.filename.lower().endswith(".pdf"):
                pdf_bytes = f0.file.read()
            else:
                img = Image.open(io.BytesIO(f0.file.read())).convert("RGB")
                buf = io.BytesIO()
                img.save(buf, format="PDF")
                pdf_bytes = buf.getvalue()

        # OCR toàn bộ PDF
        text = extract_text_from_pdf(pdf_bytes)

        if mode == "ocrText":
            return JSONResponse({"ok": True, "result": {"ocrText": text}})

        # Trích xuất placeholder cơ bản
        placeholders = simple_extract_placeholders(text)

        return JSONResponse({
            "ok": True,
            "result": {
                "ocrText": text[:5000],
                "placeholders": placeholders,
                "count_fields": len(placeholders)
            }
        })

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


# =============================
# MAIN (Render auto runs uvicorn)
# =============================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
