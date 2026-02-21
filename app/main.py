"""FastAPI application for IEEE Paper Formatter"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from dotenv import load_dotenv

from app.models import (
    UploadResponse,
    ApplyEditsRequest,
    ExportRequest,
    AskAIRequest,
    AskAIResponse,
)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="IEEE Paper Formatter",
    description="Backend API for formatting research papers to IEEE conference standards",
    version="1.0.0"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get Gemini API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("exports", exist_ok=True)

# Simple in-memory storage for formatted documents (for MVP)
# In production, use a database
document_storage = {}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "ai_mode": "enabled" if GEMINI_API_KEY else "disabled",
        "features": [
            "document_parsing",
            "grammar_correction",
            "ieee_formatting",
            "compliance_scoring",
            "docx_export",
            "pdf_export"
        ]
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a research paper
    Returns parsed document, issues, and compliance score
    
    Requirements: 1.1, 12.1, 12.2, 12.3, 12.4
    """
    from app.parser import DocumentParser
    from app.corrector import GrammarCorrector
    from app.formatter import IEEEFormatter
    from app.issue_detector import IssueDetector
    from app.compliance_scorer import ComplianceScorer
    from app.models import ProcessingResult, Fix
    import uuid
    from datetime import datetime
    
    # Validate file type
    if not file.filename.endswith('.docx'):
        raise HTTPException(
            status_code=400,
            detail="Only .docx files are supported"
        )
    
    # Check file size (10MB limit)
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=400,
            detail="File exceeds 10MB limit"
        )
    
    # Generate unique document ID
    document_id = str(uuid.uuid4())
    
    # Save file temporarily
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_filename = f"{document_id}_{timestamp}_{file.filename}"
    temp_path = os.path.join("uploads", temp_filename)
    
    try:
        # Write file to disk
        with open(temp_path, "wb") as f:
            f.write(file_content)
        
        # Parse document
        parser = DocumentParser()
        parsed_doc = parser.parse(temp_path)
        
        # Store original document for before/after comparison
        document_before = parsed_doc.model_copy(deep=True)
        
        # Correct grammar with Gemini API
        corrector = GrammarCorrector(GEMINI_API_KEY)
        corrected_sections = corrector.correct(parsed_doc.sections)
        
        # Update parsed document with corrected sections
        parsed_doc.sections = corrected_sections
        
        # Format with IEEE rules
        formatter = IEEEFormatter("rules.docx")
        formatted_doc = formatter.format(parsed_doc)
        
        # Detect issues
        issue_detector = IssueDetector()
        issues = issue_detector.detect_issues(parsed_doc)
        
        # Calculate compliance score
        scorer = ComplianceScorer()
        compliance = scorer.calculate(formatted_doc, issues)
        
        # Update formatted document with compliance score
        formatted_doc.compliance_score = compliance.score
        
        # Track changes (fixes) using ChangeTracker
        from app.change_tracker import ChangeTracker
        
        tracker = ChangeTracker()
        fixes = tracker.track_changes(document_before, formatted_doc)
        
        # Create processing result
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
                "grammar_correction_enabled": corrector.enabled
            }
        )
        
        # Store formatted document in memory for download
        document_storage[document_id] = formatted_doc
        
        return UploadResponse(processing_result=processing_result)
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )


@app.post("/apply-edits", response_model=UploadResponse)
async def apply_edits(request: ApplyEditsRequest):
    """
    Apply user edits to document
    Returns updated processing result
    
    Requirements: 5.1-5.6
    """
    from app.parser import DocumentParser
    from app.formatter import IEEEFormatter
    from app.issue_detector import IssueDetector
    from app.compliance_scorer import ComplianceScorer
    from app.user_edits import UserEditsApplicator
    from app.models import ProcessingResult, Fix
    from datetime import datetime
    
    # In a production system, we would retrieve the document from a database
    # For now, we'll try to load it from the temp path stored in metadata
    # This is a simplified implementation
    
    # For this implementation, we need the document_id to map to a stored document
    # Since we don't have persistent storage, we'll return an error for now
    # In production, you would:
    # 1. Retrieve the parsed document from database using document_id
    # 2. Apply user edits
    # 3. Re-run formatting and compliance scoring
    # 4. Return updated ProcessingResult
    
    # Placeholder implementation that shows the structure
    try:
        # TODO: Retrieve document from storage using request.document_id
        # For now, return error indicating this needs persistent storage
        
        # Example of how it would work with persistent storage:
        # parsed_doc = retrieve_document_from_db(request.document_id)
        
        # Apply user edits
        # applicator = UserEditsApplicator(allow_auto_generation=False)
        # edited_doc = applicator.apply_edits(parsed_doc, request.edits)
        
        # Re-format with IEEE rules
        # formatter = IEEEFormatter("rules.docx")
        # formatted_doc = formatter.format(edited_doc)
        
        # Re-detect issues
        # issue_detector = IssueDetector()
        # issues = issue_detector.detect_issues(edited_doc)
        
        # Re-calculate compliance score
        # scorer = ComplianceScorer()
        # compliance = scorer.calculate(formatted_doc, issues)
        
        # Update formatted document with compliance score
        # formatted_doc.compliance_score = compliance.score
        
        # Track changes
        # from app.change_tracker import ChangeTracker
        # tracker = ChangeTracker()
        # fixes = tracker.track_changes(parsed_doc, formatted_doc)
        
        # Create updated processing result
        # processing_result = ProcessingResult(...)
        
        # return UploadResponse(processing_result=processing_result)
        
        raise HTTPException(
            status_code=501,
            detail="Apply edits endpoint requires persistent storage implementation. Please use the /upload endpoint to process a new document with edits."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error applying edits: {str(e)}"
        )


@app.post("/export/docx")
async def export_docx(request: ExportRequest):
    """
    Export formatted document as .docx
    Returns downloadable file
    
    Requirements: 9.1, 9.5
    """
    from app.exporter import DocumentExporter
    from datetime import datetime
    
    # Validate format
    if request.format.lower() != "docx":
        raise HTTPException(
            status_code=400,
            detail="This endpoint only supports 'docx' format"
        )
    
    try:
        # Retrieve formatted document from in-memory storage
        if request.document_id not in document_storage:
            raise HTTPException(
                status_code=404,
                detail="Document not found. Please upload the document first."
            )
        
        formatted_doc = document_storage[request.document_id]
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"formatted_{timestamp}.docx"
        output_path = os.path.join("exports", output_filename)
        
        # Export to DOCX
        exporter = DocumentExporter()
        exporter.export_docx(formatted_doc, output_path)
        
        # Return file as downloadable response
        return FileResponse(
            path=output_path,
            filename=output_filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error exporting document: {str(e)}"
        )


@app.post("/export/pdf")
async def export_pdf(request: ExportRequest):
    """
    Export formatted document as .pdf
    Returns downloadable file
    
    Requirements: 9.2, 9.5
    """
    from app.exporter import DocumentExporter
    from datetime import datetime
    
    # Validate format
    if request.format.lower() != "pdf":
        raise HTTPException(
            status_code=400,
            detail="This endpoint only supports 'pdf' format"
        )
    
    try:
        # In a production system, we would retrieve the formatted document from database
        # For now, this is a placeholder that shows the structure
        
        # TODO: Retrieve formatted document from storage using request.document_id
        # formatted_doc = retrieve_formatted_document_from_db(request.document_id)
        
        # Generate output filename
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # output_filename = f"formatted_{timestamp}.pdf"
        # output_path = os.path.join("exports", output_filename)
        
        # Export to PDF
        # exporter = DocumentExporter()
        # exporter.export_pdf(formatted_doc, output_path)
        
        # Return file as downloadable response
        # return FileResponse(
        #     path=output_path,
        #     filename=output_filename,
        #     media_type="application/pdf"
        # )
        
        raise HTTPException(
            status_code=501,
            detail="Export endpoint requires persistent storage implementation. The formatted document must be stored after upload to enable export."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error exporting document: {str(e)}"
        )


@app.post("/ask-ai")
async def ask_ai(request: AskAIRequest):
    """
    Ask AI for assistance on specific section
    Returns AI-generated answer and suggestions
    """
    # Optional feature - implementation TBD
    raise HTTPException(status_code=501, detail="Not implemented yet")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
