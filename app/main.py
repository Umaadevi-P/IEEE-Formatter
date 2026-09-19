"""
FormatFlow – IEEE Paper Formatter
FastAPI backend integrating all 5 layers:
  A: Document Parsing
  B: IEEE Rules Engine
  C: Grammar & Language (Ollama)
  D: Document Reconstruction / Change Tracking
  E: Confidence Score Engine
"""
import os
import uuid
import logging
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from app.models import (
    UploadResponse, ApplyEditsRequest, ExportRequest,
    AskAIRequest, AskAIResponse, ProcessingResult,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FormatFlow – IEEE Paper Formatter",
    description="Local AI-powered IEEE formatting using Ollama",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("exports", exist_ok=True)

# In-memory storage: document_id -> {parsed_doc, formatted_doc, processing_result}
document_storage: Dict[str, dict] = {}

ACCEPTED_TYPES = (".docx", ".pdf")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "message": "FormatFlow API is running",
        "docs": "http://127.0.0.1:8000/docs",
        "health": "http://127.0.0.1:8000/health",
        "note": "Open index.html in your browser to use the app"
    }


@app.get("/health")
async def health_check():
    from app.ollama_service import get_ollama_status
    ollama = get_ollama_status()
    return {
        "status": "healthy",
        "version": "2.0.0",
        "ai_engine": "ollama",
        "ollama": ollama,
        "features": [
            "docx_upload", "pdf_upload",
            "ieee_formatting", "grammar_correction",
            "change_tracking", "submission_readiness_score",
            "ask_ai", "docx_export", "pdf_export",
        ],
    }


# ---------------------------------------------------------------------------
# Upload & process
# ---------------------------------------------------------------------------

@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a .docx or .pdf research paper.
    Runs all 5 processing layers and returns the full result.
    """
    fname = (file.filename or "").lower()
    if not any(fname.endswith(ext) for ext in ACCEPTED_TYPES):
        raise HTTPException(status_code=400, detail="Only .docx and .pdf files are supported")

    file_content = await file.read()
    if len(file_content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 15 MB limit")

    document_id = str(uuid.uuid4())
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".pdf" if fname.endswith(".pdf") else ".docx"
    temp_path = os.path.join("uploads", f"{document_id}_{ts}{ext}")

    try:
        with open(temp_path, "wb") as f:
            f.write(file_content)

        # --- Layer A: Parse ---
        from app.parser import DocumentParser
        parser = DocumentParser()
        parsed_doc = parser.parse(temp_path)
        document_before = parsed_doc.model_copy(deep=True)

        # --- Layer C: Grammar correction (before formatting) ---
        from app.ollama_service import correct_sections, assess_writing_quality, is_ollama_available
        if is_ollama_available():
            parsed_doc.sections = correct_sections(parsed_doc.sections)
        else:
            logger.warning("Ollama not available – skipping grammar correction")

        # --- Layer B: IEEE Rules Engine ---
        from app.ieee_rules import apply_ieee_rules
        formatted_doc, issues = apply_ieee_rules(parsed_doc, generate_missing=True)

        # --- Layer E: Scoring ---
        from app.score_engine import calculate_readiness_score
        ai_quality = None
        if is_ollama_available():
            ai_quality = assess_writing_quality(formatted_doc.sections)
        compliance = calculate_readiness_score(formatted_doc, issues, ai_quality)
        formatted_doc.compliance_score = compliance.score

        # --- Layer D: Change tracking ---
        from app.change_tracker import ChangeTracker
        tracker = ChangeTracker()
        fixes = tracker.track_changes(document_before, formatted_doc)

        # --- Assemble result ---
        processing_result = ProcessingResult(
            status="success",
            document_before=document_before,
            document_after=formatted_doc,
            issues=issues,
            fixes=fixes,
            compliance=compliance,
            metadata={
                "document_id": document_id,
                "original_filename": file.filename,
                "temp_path": temp_path,
                "processed_at": datetime.now().isoformat(),
                "ai_grammar_enabled": is_ollama_available(),
                "total_sections": len(formatted_doc.sections),
                "total_words": sum(s.word_count for s in formatted_doc.sections),
                "issues_count": len(issues),
                "fixes_count": len(fixes),
            },
        )

        # Store for download
        document_storage[document_id] = {
            "formatted_doc": formatted_doc,
            "processing_result": processing_result,
            "temp_path": temp_path,
        }

        return UploadResponse(processing_result=processing_result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing document")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


# ---------------------------------------------------------------------------
# Apply user edits
# ---------------------------------------------------------------------------

@app.post("/apply-edits", response_model=UploadResponse)
async def apply_edits(request: ApplyEditsRequest):
    """
    Apply user-provided edits (author, affiliation, keywords, section corrections)
    to a previously processed document and re-run the full pipeline.
    """
    stored = document_storage.get(request.document_id)
    if not stored:
        raise HTTPException(
            status_code=404,
            detail="Document not found. Please upload the document again."
        )

    try:
        from app.user_edits import UserEditsApplicator
        from app.ieee_rules import apply_ieee_rules
        from app.score_engine import calculate_readiness_score
        from app.change_tracker import ChangeTracker
        from app.ollama_service import correct_sections, assess_writing_quality, is_ollama_available

        # Get original parsed document from stored result
        pr = stored["processing_result"]
        parsed_doc = pr.document_before.model_copy(deep=True)
        document_before = parsed_doc.model_copy(deep=True)

        # Apply user edits
        applicator = UserEditsApplicator()
        edited_doc = applicator.apply_edits(parsed_doc, request.edits)

        # Grammar correction
        if is_ollama_available():
            edited_doc.sections = correct_sections(edited_doc.sections)

        # Re-format
        formatted_doc, issues = apply_ieee_rules(edited_doc, generate_missing=True)

        # Re-score
        ai_quality = None
        if is_ollama_available():
            ai_quality = assess_writing_quality(formatted_doc.sections)
        compliance = calculate_readiness_score(formatted_doc, issues, ai_quality)
        formatted_doc.compliance_score = compliance.score

        # Track changes
        tracker = ChangeTracker()
        fixes = tracker.track_changes(document_before, formatted_doc)

        processing_result = ProcessingResult(
            status="success",
            document_before=document_before,
            document_after=formatted_doc,
            issues=issues,
            fixes=fixes,
            compliance=compliance,
            metadata={
                **pr.metadata,
                "edits_applied": True,
                "processed_at": datetime.now().isoformat(),
            },
        )

        # Update storage
        document_storage[request.document_id]["formatted_doc"] = formatted_doc
        document_storage[request.document_id]["processing_result"] = processing_result

        return UploadResponse(processing_result=processing_result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error applying edits")
        raise HTTPException(status_code=500, detail=f"Error applying edits: {str(e)}")


# ---------------------------------------------------------------------------
# Ask AI (text selection feature)
# ---------------------------------------------------------------------------

@app.post("/ask-ai")
async def ask_ai(request: AskAIRequest):
    """
    Apply an AI instruction to a selected piece of text.
    Used by the text-selection menu in the preview screen.
    """
    from app.ollama_service import apply_instruction_to_text, is_ollama_available

    if not is_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="Ollama AI is not available. Make sure Ollama is running and the model is pulled."
        )

    if not request.selected_text.strip():
        raise HTTPException(status_code=400, detail="selected_text cannot be empty")

    if not request.instruction.strip():
        raise HTTPException(status_code=400, detail="instruction cannot be empty")

    try:
        result = apply_instruction_to_text(
            selected_text=request.selected_text,
            instruction=request.instruction,
            section_type=request.section_type,
        )

        # If document_id provided, persist the change in the stored document
        if request.document_id and request.section_id and request.document_id in document_storage:
            _apply_inline_edit(
                request.document_id,
                request.section_id,
                request.selected_text,
                result["improved_text"],
            )

        return AskAIResponse(
            original_text=request.selected_text,
            improved_text=result["improved_text"],
            explanation=result["explanation"],
            changes_made=result["changes_made"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in ask-ai")
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")


def _apply_inline_edit(
    document_id: str,
    section_id: str,
    original_text: str,
    improved_text: str,
) -> None:
    """Persist an inline AI edit into the stored formatted document."""
    stored = document_storage.get(document_id)
    if not stored:
        return
    fmtdoc = stored["formatted_doc"]
    for section in fmtdoc.sections:
        if section.id == section_id and original_text in section.content:
            section.content = section.content.replace(original_text, improved_text, 1)
            section.word_count = len(section.content.split())
            break
    # Also update the processing result's document_after
    pr = stored["processing_result"]
    for section in pr.document_after.sections:
        if section.id == section_id and original_text in section.content:
            section.content = section.content.replace(original_text, improved_text, 1)
            section.word_count = len(section.content.split())
            break


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@app.post("/export/docx")
async def export_docx(request: ExportRequest):
    """Export formatted document as .docx"""
    if request.format.lower() != "docx":
        raise HTTPException(status_code=400, detail="Use format='docx'")

    stored = document_storage.get(request.document_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Document not found. Please upload first.")

    try:
        from app.exporter import DocumentExporter
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"formatted_{ts}.docx"
        out_path = os.path.join("exports", out_name)

        exporter = DocumentExporter()
        exporter.export_docx(stored["formatted_doc"], out_path)

        return FileResponse(
            path=out_path,
            filename=out_name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:
        logger.exception("DOCX export failed")
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


@app.post("/export/pdf")
async def export_pdf(request: ExportRequest):
    """Export formatted document as .pdf"""
    if request.format.lower() != "pdf":
        raise HTTPException(status_code=400, detail="Use format='pdf'")

    stored = document_storage.get(request.document_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Document not found. Please upload first.")

    try:
        from app.exporter import DocumentExporter
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"formatted_{ts}.pdf"
        out_path = os.path.join("exports", out_name)

        exporter = DocumentExporter()
        exporter.export_pdf(stored["formatted_doc"], out_path)

        return FileResponse(
            path=out_path,
            filename=out_name,
            media_type="application/pdf",
        )
    except Exception as e:
        logger.exception("PDF export failed")
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


@app.post("/simulate-reviewer")
async def simulate_reviewer_endpoint(request: Request):
    from app.ollama_service import simulate_reviewer, is_ollama_available
    if not is_ollama_available():
        raise HTTPException(status_code=503, detail="Ollama not available")
    request_body = await request.json()
    doc_id = request_body.get("document_id")
    if not doc_id or doc_id not in document_storage:
        raise HTTPException(status_code=404, detail="Document not found")
    sections = document_storage[doc_id]["formatted_doc"].sections
    result = simulate_reviewer(sections)
    return result


@app.post("/check-terminology")
async def check_terminology(request: Request):
    from app.ollama_service import check_terminology_consistency, is_ollama_available
    if not is_ollama_available():
        raise HTTPException(status_code=503, detail="Ollama not available")
    request_body = await request.json()
    doc_id = request_body.get("document_id")
    if not doc_id or doc_id not in document_storage:
        raise HTTPException(status_code=404, detail="Document not found")
    sections = document_storage[doc_id]["formatted_doc"].sections
    result = check_terminology_consistency(sections)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
