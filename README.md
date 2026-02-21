# IEEE Paper Formatter

AI-powered research paper formatter that converts manuscripts to IEEE conference standards.

## 🚀 Quick Start

**One-Click Launch**: Double-click `LAUNCH.bat`

That's it! The system will:
- ✅ Start the backend server
- ✅ Open the frontend in your browser
- ✅ Be ready to format papers

## 📄 Test It

Upload the test document: `uploads/Ocean_Exploration_Human_Impact.docx`

## 📚 Documentation

- **Complete Guide**: `START_SYSTEM.md`
- **Integration Details**: `INTEGRATION_COMPLETE.md`
- **Requirements**: `.kiro/specs/ieee-paper-formatter/requirements.md`
- **Design**: `.kiro/specs/ieee-paper-formatter/design.md`

## ✨ Features

- Document parsing and structure extraction
- Grammar correction (with Gemini API)
- IEEE formatting rules application
- Section reordering
- Issue detection
- Compliance scoring
- Citation conversion
- Change tracking
- Before/After comparison

## 🧪 Testing

All 91 tests passing:
```bash
pytest tests/ -v
```

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.12
- **Frontend**: HTML, CSS, JavaScript
- **Document Processing**: python-docx
- **Testing**: pytest, hypothesis
- **AI**: Google Gemini API (optional)

## 📊 Status

✅ Backend: Fully functional  
✅ Frontend: Integrated with backend  
✅ Tests: 91/91 passing  
✅ Integration: Complete, no errors  

## Project Structure

```
.
├── app/                      # Backend application
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models
│   ├── parser.py            # Document parser
│   ├── corrector.py         # Grammar corrector
│   ├── formatter.py         # IEEE formatter
│   ├── issue_detector.py    # Issue detection
│   ├── compliance_scorer.py # Compliance scoring
│   ├── exporter.py          # Document export
│   ├── citation_converter.py # Citation conversion
│   ├── change_tracker.py    # Change tracking
│   └── user_edits.py        # User edits handler
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── property/            # Property-based tests
├── uploads/                 # Uploaded documents
├── exports/                 # Generated documents
├── index.html               # Frontend UI
├── LAUNCH.bat              # One-click launcher
├── START_SYSTEM.md         # Complete guide
└── requirements.txt        # Python dependencies
```

## API Endpoints

- `GET /health` - Health check
- `POST /upload` - Upload and process document
- `POST /apply-edits` - Apply user edits (requires storage)
- `POST /export/docx` - Export as DOCX (requires storage)
- `POST /export/pdf` - Export as PDF (requires storage)

## Manual Setup

If you prefer manual setup:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file (optional):
```
GEMINI_API_KEY=your_api_key_here
```

3. Start backend:
```bash
python -m uvicorn app.main:app --reload
```

4. Open `index.html` in your browser

---

**Need help?** See `START_SYSTEM.md` for detailed instructions.
