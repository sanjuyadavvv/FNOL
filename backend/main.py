from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from extractor import extract_text_from_file, process_document_text
from router import determine_route

app = FastAPI(title="FNOL Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


def _build_response(document_text: str) -> dict:
    if not document_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the document.",
        )

    result = process_document_text(document_text)
    route, reasoning = determine_route(
        result["extractedFields"], result["missingFields"]
    )

    if result["invalidDates"]:
        invalid_list = ", ".join(result["invalidDates"])
        reasoning += f" Invalid date format detected ({invalid_list})."

    return {
        **result,
        "recommendedRoute": route,
        "reasoning": reasoning,
    }


async def _process_upload(file: UploadFile) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    allowed = (".pdf", ".txt")
    if not file.filename.lower().endswith(allowed):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload a PDF or TXT FNOL document.",
        )

    file_bytes = await file.read()
    document_text = extract_text_from_file(file_bytes, file.filename)
    return _build_response(document_text)


@app.post("/api/process-fnol")
async def process_fnol(request: Request):
    content_type = request.headers.get("content-type", "")

    try:
        if "application/json" in content_type:
            body = await request.json()
            pasted = body.get("text") if isinstance(body, dict) else None
            if not pasted or not str(pasted).strip():
                raise HTTPException(status_code=400, detail="FNOL text cannot be empty.")
            return _build_response(str(pasted).strip())

        if "multipart/form-data" in content_type:
            form = await request.form()
            form_text = form.get("text")
            if form_text and str(form_text).strip():
                return _build_response(str(form_text).strip())

            form_file = form.get("file")
            if form_file and hasattr(form_file, "filename") and form_file.filename:
                return await _process_upload(form_file)

        raise HTTPException(
            status_code=400,
            detail="Provide a PDF/TXT file or paste FNOL text.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {exc}",
        ) from exc
