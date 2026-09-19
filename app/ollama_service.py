"""
Layer C: Grammar and Language Analysis Layer
Uses Ollama (local AI) for grammar correction, academic writing improvement,
and text analysis. No external API keys required.

PERFORMANCE NOTES:
- Grammar correction runs sections concurrently via ThreadPoolExecutor
- num_predict is capped to avoid runaway generation
- Sections under MIN_WORDS_FOR_CORRECTION are skipped
- Hard per-call timeout prevents hanging
"""
import os
import logging
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from typing import List, Optional, Dict, Any

from app.models import Section, GrammarSuggestion

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# Per-call HTTP timeout (seconds). Grammar calls get a shorter budget.
OLLAMA_TIMEOUT         = int(os.getenv("OLLAMA_TIMEOUT", "90"))
GRAMMAR_CALL_TIMEOUT   = int(os.getenv("GRAMMAR_TIMEOUT", "45"))   # fast grammar calls
ANALYSIS_CALL_TIMEOUT  = int(os.getenv("ANALYSIS_TIMEOUT", "90"))  # reviewer / terminology

# Only correct sections with at least this many words (tiny sections aren't worth an API call)
MIN_WORDS_FOR_CORRECTION = int(os.getenv("MIN_WORDS_FOR_CORRECTION", "20"))

# Max concurrent grammar correction threads
MAX_GRAMMAR_WORKERS = int(os.getenv("MAX_GRAMMAR_WORKERS", "3"))

# Cap output tokens — grammar correction doesn't need huge responses
GRAMMAR_MAX_TOKENS   = 1024
ANALYSIS_MAX_TOKENS  = 512
SELECTION_MAX_TOKENS = 768


# ---------------------------------------------------------------------------
# Core Ollama caller
# ---------------------------------------------------------------------------

def _call_ollama(
    prompt: str,
    system: str = "",
    timeout: int = None,
    num_predict: int = None,
) -> Optional[str]:
    """
    Call the Ollama /api/generate endpoint.
    Returns response text or None on any failure.
    """
    t = timeout or OLLAMA_TIMEOUT
    np = num_predict or ANALYSIS_MAX_TOKENS

    try:
        payload: Dict[str, Any] = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": np,
                # Keep context small for speed
                "num_ctx": 4096,
            },
        }
        if system:
            payload["system"] = system

        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=t,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()

    except requests.exceptions.Timeout:
        logger.warning(f"Ollama call timed out after {t}s")
        return None
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama — is `ollama serve` running?")
        return None
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def is_ollama_available() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=4)
        if resp.status_code != 200:
            return False
        models = [m.get("name", "") for m in resp.json().get("models", [])]
        base = OLLAMA_MODEL.split(":")[0]
        return any(OLLAMA_MODEL in n or base in n for n in models)
    except Exception:
        return False


def get_ollama_status() -> Dict[str, Any]:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=4)
        if resp.status_code != 200:
            return {"available": False, "model": OLLAMA_MODEL, "reason": "server_not_responding"}
        models = [m.get("name", "") for m in resp.json().get("models", [])]
        base = OLLAMA_MODEL.split(":")[0]
        model_ready = any(OLLAMA_MODEL in n or base in n for n in models)
        return {
            "available": model_ready,
            "model": OLLAMA_MODEL,
            "server": OLLAMA_BASE_URL,
            "available_models": models,
            "reason": "ready" if model_ready else "model_not_pulled",
        }
    except Exception as e:
        return {"available": False, "model": OLLAMA_MODEL, "reason": str(e)}


# ---------------------------------------------------------------------------
# Grammar correction — concurrent
# ---------------------------------------------------------------------------

GRAMMAR_SYSTEM = (
    "You are a grammar correction assistant for academic papers. "
    "Fix ONLY grammar, spelling, and punctuation. "
    "Do NOT add content. Do NOT remove content. Do NOT summarise. "
    "Return ONLY the corrected text."
)

# Section types that don't need grammar correction
_SKIP_GRAMMAR = {"Title", "Authors", "Affiliation", "References", "Keywords"}


def correct_text_grammar(text: str) -> str:
    """Fix grammar in a single text block. Falls back to original on failure."""
    if not text or len(text.split()) < MIN_WORDS_FOR_CORRECTION:
        return text

    # Truncate very long sections — correct first 800 words, keep rest as-is
    words = text.split()
    if len(words) > 800:
        to_correct = " ".join(words[:800])
        remainder  = " ".join(words[800:])
        corrected_part = _do_grammar_call(to_correct)
        return corrected_part + " " + remainder
    return _do_grammar_call(text)


def _do_grammar_call(text: str) -> str:
    prompt = (
        f"Fix grammar, spelling, and punctuation only. Return ONLY the corrected text.\n\n"
        f"TEXT:\n{text}\n\nCORRECTED TEXT:"
    )
    result = _call_ollama(
        prompt,
        system=GRAMMAR_SYSTEM,
        timeout=GRAMMAR_CALL_TIMEOUT,
        num_predict=GRAMMAR_MAX_TOKENS,
    )
    if result:
        # Strip any preamble the model might prepend
        for prefix in ["CORRECTED TEXT:", "Corrected text:", "Here is", "Here's"]:
            if result.startswith(prefix):
                result = result[result.index("\n") + 1:].strip() if "\n" in result else result[len(prefix):].strip()
        return result
    return text


def correct_sections(sections: List[Section]) -> List[Section]:
    """
    Grammar-correct all eligible sections IN PARALLEL.
    Sections are corrected concurrently up to MAX_GRAMMAR_WORKERS threads.
    """
    # Split into sections that need correction vs those that don't
    needs_correction = []
    skip_map: Dict[str, Section] = {}   # id -> already-done copy

    for section in sections:
        s = section.model_copy(deep=True)
        if (s.type.value in _SKIP_GRAMMAR
                or not s.content
                or len(s.content.split()) < MIN_WORDS_FOR_CORRECTION):
            skip_map[s.id] = s
        else:
            needs_correction.append(s)

    if not needs_correction:
        logger.info("No sections needed grammar correction")
        return list(skip_map.values())

    logger.info(
        f"Grammar correcting {len(needs_correction)} sections "
        f"concurrently (max {MAX_GRAMMAR_WORKERS} workers)..."
    )

    corrected_map: Dict[str, Section] = {}

    def _correct_one(s: Section) -> Section:
        s.content = correct_text_grammar(s.content)
        return s

    with ThreadPoolExecutor(max_workers=MAX_GRAMMAR_WORKERS) as executor:
        future_to_id = {executor.submit(_correct_one, s): s.id for s in needs_correction}
        for future in as_completed(future_to_id):
            sid = future_to_id[future]
            try:
                corrected_map[sid] = future.result(timeout=GRAMMAR_CALL_TIMEOUT + 5)
            except Exception as exc:
                logger.error(f"Grammar correction failed for section {sid}: {exc}")
                # Fall back to the original uncorrected section
                orig = next(s for s in needs_correction if s.id == sid)
                corrected_map[sid] = orig

    # Reconstruct in original order
    result = []
    for section in sections:
        sid = section.id
        if sid in corrected_map:
            result.append(corrected_map[sid])
        elif sid in skip_map:
            result.append(skip_map[sid])
        else:
            result.append(section.model_copy(deep=True))

    logger.info(f"Grammar correction done — {len(result)} sections")
    return result


# ---------------------------------------------------------------------------
# AI text selection (ask-AI)
# ---------------------------------------------------------------------------

def apply_instruction_to_text(
    selected_text: str,
    instruction: str,
    section_type: Optional[str] = None,
) -> Dict[str, Any]:
    context = f" (from the {section_type} section)" if section_type else ""

    system = (
        "You are an expert academic writing editor. "
        "Apply the given instruction to the text and return a JSON object with keys: "
        "'improved_text', 'explanation', 'changes_made' (array of short strings). "
        "Return ONLY valid JSON."
    )

    prompt = (
        f"TEXT{context}: \"{selected_text[:600]}\"\n\n"
        f"INSTRUCTION: {instruction}\n\n"
        f"Return JSON: {{improved_text, explanation, changes_made}}"
    )

    raw = _call_ollama(
        prompt,
        system=system,
        timeout=ANALYSIS_CALL_TIMEOUT,
        num_predict=SELECTION_MAX_TOKENS,
    )

    if not raw:
        return {
            "improved_text": selected_text,
            "explanation": "AI unavailable — returning original text.",
            "changes_made": [],
        }

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        data = json.loads(cleaned.strip())
        return {
            "improved_text": data.get("improved_text", selected_text),
            "explanation":   data.get("explanation", ""),
            "changes_made":  data.get("changes_made", []),
        }
    except (json.JSONDecodeError, KeyError):
        return {
            "improved_text": raw.strip(),
            "explanation": "Text improved by AI.",
            "changes_made": ["Text rewritten per instruction"],
        }


# ---------------------------------------------------------------------------
# Missing section generation
# ---------------------------------------------------------------------------

def generate_section_content(section_type: str, document_context: str) -> str:
    system = (
        "You are a professional academic writing assistant for IEEE conference papers. "
        "Generate concise professional content for the requested section based ONLY on the provided context. "
        "Return plain text only. Be brief."
    )
    word_targets = {
        "Abstract":   "150-200 words",
        "Introduction": "150-250 words",
        "Conclusion": "100-150 words",
        "Keywords":   "5-7 comma-separated keywords",
    }
    target = word_targets.get(section_type, "80-150 words")

    prompt = (
        f"Write a {section_type} section ({target}) for this IEEE paper.\n\n"
        f"PAPER CONTEXT:\n{document_context[:2000]}\n\n"
        f"{section_type.upper()}:"
    )
    result = _call_ollama(
        prompt,
        system=system,
        timeout=ANALYSIS_CALL_TIMEOUT,
        num_predict=512,
    )
    return result or f"[{section_type} — please add content manually]"


# ---------------------------------------------------------------------------
# Writing quality assessment (for score engine)
# ---------------------------------------------------------------------------

def assess_writing_quality(sections: List[Section]) -> Dict[str, Any]:
    key_types = {"Abstract", "Introduction", "Conclusion"}
    excerpts = []
    for s in sections:
        if s.type.value in key_types and s.content:
            # Only use first 100 words per section to keep prompt tiny
            words = s.content.split()[:100]
            excerpts.append(f"[{s.type.value}]: {' '.join(words)}")

    if not excerpts:
        return {"grammar_score": 70, "clarity_score": 70, "academic_tone_score": 70, "overall_feedback": ""}

    combined = "\n".join(excerpts)

    system = (
        "You are an IEEE paper reviewer. Rate the writing quality briefly. "
        "Return ONLY JSON with keys: grammar_score (0-100), clarity_score (0-100), "
        "academic_tone_score (0-100), overall_feedback (1 sentence)."
    )
    prompt = f"Rate this paper excerpt:\n\n{combined}\n\nReturn JSON only."

    raw = _call_ollama(
        prompt,
        system=system,
        timeout=ANALYSIS_CALL_TIMEOUT,
        num_predict=ANALYSIS_MAX_TOKENS,
    )

    if not raw:
        return {"grammar_score": 70, "clarity_score": 70, "academic_tone_score": 70, "overall_feedback": ""}

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        return json.loads(cleaned.strip())
    except Exception:
        return {"grammar_score": 70, "clarity_score": 70, "academic_tone_score": 70, "overall_feedback": raw[:150]}


# ---------------------------------------------------------------------------
# Reviewer Simulation
# ---------------------------------------------------------------------------

def simulate_reviewer(sections: List[Section]) -> Dict[str, Any]:
    key_types = {"Abstract", "Introduction", "Conclusion"}
    excerpts = []
    for s in sections:
        if s.type.value in key_types and s.content:
            words = s.content.split()[:150]
            excerpts.append(f"[{s.type.value}]: {' '.join(words)}")

    if not excerpts:
        return {"critiques": ["Insufficient content to review."], "verdict": "Incomplete", "summary": "", "strengths": []}

    combined = "\n\n".join(excerpts)

    system = (
        "You are a strict IEEE conference paper reviewer. "
        "Return ONLY a JSON object with keys: "
        "'verdict' (one of: Strong Accept, Accept, Weak Accept, Weak Reject, Reject), "
        "'summary' (2 sentences), "
        "'critiques' (array of 3-4 short strings), "
        "'strengths' (array of 1-2 short strings). "
        "Be concise."
    )
    prompt = f"First-pass review of this IEEE paper:\n\n{combined}\n\nReturn JSON only."

    raw = _call_ollama(
        prompt,
        system=system,
        timeout=ANALYSIS_CALL_TIMEOUT,
        num_predict=ANALYSIS_MAX_TOKENS,
    )
    if not raw:
        return {"verdict": "Unavailable", "summary": "AI not available.", "critiques": [], "strengths": []}

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        return json.loads(cleaned.strip())
    except Exception:
        return {"verdict": "See feedback", "summary": raw[:200], "critiques": [], "strengths": []}


# ---------------------------------------------------------------------------
# Terminology Consistency Checker
# ---------------------------------------------------------------------------

def check_terminology_consistency(sections: List[Section]) -> Dict[str, Any]:
    body_types = {"Introduction", "Methodology", "Results", "Conclusion"}
    full_text = ""
    for s in sections:
        if s.type.value in body_types and s.content:
            full_text += s.content + "\n\n"

    if len(full_text.split()) < 80:
        return {"inconsistencies": [], "suggestion": "Not enough content to check."}

    system = (
        "You are a technical writing expert. "
        "Find cases where the same concept is called by different names. "
        "Return ONLY JSON with keys: "
        "'inconsistencies' (array of {term_variants: [], recommendation: string}), "
        "'suggestion' (1 sentence). Max 4 inconsistencies. Be brief."
    )
    prompt = (
        f"Find terminology inconsistencies:\n\n{full_text[:2500]}\n\nReturn JSON only."
    )

    raw = _call_ollama(
        prompt,
        system=system,
        timeout=ANALYSIS_CALL_TIMEOUT,
        num_predict=ANALYSIS_MAX_TOKENS,
    )
    if not raw:
        return {"inconsistencies": [], "suggestion": "AI unavailable."}

    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        return json.loads(cleaned.strip())
    except Exception:
        return {"inconsistencies": [], "suggestion": raw[:150]}
