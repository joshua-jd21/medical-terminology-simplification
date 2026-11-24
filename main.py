import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from terminology_simplifier import simplify_medical_text
from document_reader import extract_document_text
from simplified_pdf_generator import generate_simplified_pdf


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="MediSimplify AI",
    description="NLP-Based Medical Terminology Simplification System",
    version="1.0.0"
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
async def root():

    return {
        "status": "online",
        "message": "MediSimplify AI backend is running"
    }


@app.get("/health")
async def health():

    return {
        "status": "healthy"
    }


# ============================================================
# MEDICAL TERMINOLOGY SIMPLIFICATION
# ============================================================

@app.post("/simplify")
async def simplify(data: dict):

    text = data.get("text", "")

    if not isinstance(text, str) or not text.strip():

        raise HTTPException(
            status_code=400,
            detail="Please enter medical text."
        )

    return simplify_medical_text(text)


# ============================================================
# MEDICAL DOCUMENT UPLOAD
# ============================================================

@app.post("/upload_document")
async def upload_document(request: Request):

    try:

        form = await request.form()
        file = form.get("file")

        if file is None or not hasattr(file, "read"):

            raise HTTPException(
                status_code=400,
                detail="Please upload a document."
            )

        filename = file.filename or ""

        file_content = await file.read(
            5 * 1024 * 1024 + 1
        )
        await file.close()

        if len(file_content) > 5 * 1024 * 1024:

            raise HTTPException(
                status_code=413,
                detail="File size must not exceed 5 MB."
            )

        text = extract_document_text(
            file_content,
            filename
        )

        if not text.strip():

            raise HTTPException(
                status_code=400,
                detail="No readable text found in the document."
            )

        result = simplify_medical_text(text)

        result["filename"] = filename

        return result

    except HTTPException:

        raise

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        print("Upload error:", repr(e))
        raise HTTPException(
            status_code=400,
            detail="Unable to read the uploaded document."
        )


# ============================================================
# DOWNLOAD SIMPLIFIED MEDICAL PDF
# ============================================================

@app.post("/download_simplified_pdf")
async def download_simplified_pdf(data: dict):

    text = data.get("text", "")

    if not isinstance(text, str) or not text.strip():

        raise HTTPException(
            status_code=400,
            detail="Please provide medical text."
        )

    try:

        result = simplify_medical_text(text)

        pdf_content = generate_simplified_pdf(result)

        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                'attachment; filename="simplified_medical_report.pdf"'
            }
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Unable to generate PDF."
        )


# ============================================================
# SERVER ENTRY POINT
# ============================================================

if __name__ == "__main__":

    import uvicorn

    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        reload=False
    )