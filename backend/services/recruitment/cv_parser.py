# backend/services/recruitment/cv_parser.py
#
# CV parsing pipeline — extracts structured fields from raw CV text.
# Uses regex and heuristics only for field extraction (no Groq).
# Groq is reserved for generation tasks only (summaries, outreach, JD expansion).
#
# Parsing chain:
#   PDF  → pdfplumber → pypdf → PyPDF2 (fallback)
#   DOCX → python-docx
#   TXT  → plain read
#   CSV  → Kaggle Resume_str column
#   ZIP  → extract all valid files inside

import re
import io
import hashlib
import os
from typing import Optional


# ── Domain-specific skill keywords ───────────────────────────────────────────
# Organized by domain — prioritizes technical/certified skills over soft skills

DOMAIN_SKILLS = {
    # Contracts & Claims
    "fidic": "FIDIC", "eot": "EOT", "clac": "CLAC", "ciccm": "CICCM",
    "fciArb": "FCIArb", "fciArb".lower(): "FCIArb",
    "arbitration": "Arbitration", "claims management": "Claims Management",
    "contract administration": "Contract Administration",
    "variation orders": "Variation Orders", "dispute resolution": "Dispute Resolution",
    "subcontract": "Subcontracts", "tendering": "Tendering",
    "procurement": "Procurement", "pre-award": "Pre-Award",
    "post-award": "Post-Award", "nec": "NEC", "jct": "JCT",

    # Estimation & Quantity Surveying
    "bill of quantities": "BOQ", "boq": "BOQ", "quantity surveying": "Quantity Surveying",
    "cost estimation": "Cost Estimation", "material takeoff": "Material Takeoff",
    "primavera": "Primavera", "cost planning": "Cost Planning",

    # Engineering Tools
    "autocad": "AutoCAD", "tekla": "Tekla", "etabs": "ETABS",
    "sap2000": "SAP2000", "revit": "Revit", "staad": "STAAD",
    "solidworks": "SolidWorks", "ansys": "ANSYS",

    # Project Management
    "pmp": "PMP", "prince2": "PRINCE2", "ms project": "MS Project",
    "project management": "Project Management", "agile": "Agile", "scrum": "Scrum",

    # Data & Analytics
    "power bi": "Power BI", "powerbi": "Power BI", "tableau": "Tableau",
    "python": "Python", "sql": "SQL", "excel": "Excel",
    "data analysis": "Data Analysis", "machine learning": "Machine Learning",
    "tensorflow": "TensorFlow", "pandas": "Pandas", "numpy": "NumPy",

    # ERP Systems
    "sap": "SAP", "oracle": "Oracle", "salesforce": "Salesforce",

    # Construction
    "civil engineering": "Civil Engineering", "structural engineering": "Structural Engineering",
    "seismic": "Seismic Engineering", "geotechnical": "Geotechnical",

    # Finance & Legal
    "ifrs": "IFRS", "accounting": "Accounting", "auditing": "Auditing",
    "llm": "LLM", "mba": "MBA",

    # Sales & Business
    "crm": "CRM", "business development": "Business Development",

    # Cloud & IT
    "aws": "AWS", "azure": "Azure", "docker": "Docker",
    "kubernetes": "Kubernetes", "javascript": "JavaScript",
    "react": "React", "node": "Node.js",
}


def _extract_skills(text: str) -> str:
    """Extract domain-specific skills from CV text."""
    text_lower = text.lower()
    found = []
    seen = set()

    # First pass — domain skills in priority order
    for keyword, display in DOMAIN_SKILLS.items():
        if keyword in text_lower and display not in seen:
            found.append(display)
            seen.add(display)
        if len(found) >= 8:
            break

    return ", ".join(found) if found else ""


def _extract_name(text: str) -> Optional[str]:
    """Extract candidate name from first few lines."""
    lines = [l.strip() for l in text.split("\n") if l.strip()][:8]
    skip = {"resume", "curriculum", "vitae", "cv", "profile", "email",
            "phone", "mobile", "address", "linkedin", "objective", "summary"}
    for line in lines:
        line = re.sub(r'[^\w\s\-\.]', '', line).strip()
        words = line.split()
        if 2 <= len(words) <= 5:
            if not any(s in line.lower() for s in skip):
                if not re.search(r'\d', line):
                    if line[0].isupper():
                        return line.title()
    return None


def _extract_email(text: str) -> Optional[str]:
    match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    return match.group(0) if match else None


def _extract_current_title(text: str) -> Optional[str]:
    """Extract current/most recent job title. Skips personal info lines."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Lines to skip — personal info patterns
    skip_patterns = [
        r'@',                          # email
        r'linkedin',                   # linkedin
        r'http',                       # any URL
        r'\+?\d[\d\s\-\.]{7,}',       # phone number
        r'\b(street|st\.|avenue|ave|road|rd|city|cairo|dubai|egypt|ksa|saudi|uae)\b',
        r'\b(born|nationality|marital|military|exempted)\b',
        r'^\d',                        # starts with number
    ]

    def is_personal_info(line: str) -> bool:
        line_lower = line.lower()
        return any(re.search(p, line_lower) for p in skip_patterns)

    # Look for explicit current role labels
    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in ["current role", "current position", "current title", "job title:"]):
            parts = re.split(r'[:–\-]', line, 1)
            if len(parts) > 1 and not is_personal_info(parts[1]):
                return parts[1].strip()

    # Find title near "present" date range
    text_lower = text.lower()
    present_idx = text_lower.find("present")
    if present_idx > 0:
        snippet = text[max(0, present_idx - 400):present_idx]
        snippet_lines = [l.strip() for l in snippet.split("\n") if l.strip()]
        for line in reversed(snippet_lines):
            if is_personal_info(line):
                continue
            if 2 <= len(line.split()) <= 8:
                if not re.search(r'\d{4}', line):
                    if line[0].isupper():
                        return line

    # Fall back to first non-personal non-name line
    non_empty = [l for l in lines if len(l) > 3]
    for line in non_empty[1:4]:
        if not is_personal_info(line):
            if len(line.split()) <= 8 and not re.search(r'\d{4}', line):
                return line

    return None


def _extract_current_company(text: str) -> Optional[str]:
    """Extract most recent employer."""
    patterns = [
        r'(?:at|with|employer|company)[:\s]+([A-Z][^\n,\.]{2,40})',
        r'(?:currently at|working at|employed at)[:\s]+([A-Z][^\n,\.]{2,40})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Find company near "present"
    text_lower = text.lower()
    present_idx = text_lower.find("present")
    if present_idx > 0:
        snippet = text[max(0, present_idx - 400):present_idx + 50]
        companies = re.findall(r'\b([A-Z][A-Za-z\s&\.\-]{3,35}(?:Ltd|LLC|Inc|Co|Corp|Group|Engineering|Consulting|International|Company)?)\b', snippet)
        if companies:
            return companies[-1].strip()
    return None


def _extract_years_experience(text: str) -> float:
    """Extract total years of professional experience."""
    text_lower = text.lower()

    # Method 1: explicit statement
    patterns = [
        r"(\d+)\+?\s*years?\s+of\s+(?:professional\s+)?experience",
        r"(\d+)\+?\s*years?\s+(?:professional\s+)?(?:work\s+)?experience",
        r"experience\s+of\s+(\d+)\+?\s*years?",
        r"over\s+(\d+)\s+years?\s+of\s+experience",
    ]
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            val = float(match.group(1))
            if 1 <= val <= 45:
                return val

    # Method 2: find job date ranges in experience section only
    exp_match = re.search(
        r'(experience|employment|work history|career|professional background)(.*?)(education|skills|certifications|languages|references)',
        text_lower, re.DOTALL
    )
    section = exp_match.group(2) if exp_match else text_lower[:3000]

    date_ranges = re.findall(
        r'(20\d{2})\s*[-–—to]+\s*(?:20\d{2}|present|current|now|till\s+date|to\s+date)',
        section
    )
    if date_ranges:
        start_years = [int(y) for y in date_ranges if 1990 <= int(y) <= 2024]
        if start_years:
            return float(min(40, max(1, 2025 - min(start_years))))

    return 0.0


def _extract_seniority(text: str, years: float) -> str:
    """Determine seniority level."""
    text_lower = text.lower()
    senior_titles = ["senior", "lead", "principal", "director", "head of",
                     "vp ", "vice president", "chief", "manager", "supervisor"]
    junior_titles = ["junior", "intern", "trainee", "graduate", "entry level", "assistant"]

    if any(t in text_lower for t in senior_titles) or years >= 8:
        return "senior"
    if any(t in text_lower for t in junior_titles) or years < 2:
        return "junior"
    return "mid"


def _extract_fields(text: str, source_category: Optional[str]) -> dict:
    """Extract all structured fields from raw CV text using regex."""
    years = _extract_years_experience(text)
    return {
        "raw_cv_text":      text,
        "name":             _extract_name(text),
        "email":            _extract_email(text),
        "current_title":    _extract_current_title(text),
        "current_company":  _extract_current_company(text),
        "skills":           _extract_skills(text),
        "years_experience": years,
        "seniority_level":  _extract_seniority(text, years),
        "industry":         source_category,
        "tenure_months":    0.0,
        "is_employed":      1 if "present" in text.lower() or "current" in text.lower() else 0,
        "job_changes":      0,
    }


def _hash_cv(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


# ── PDF Parsing ───────────────────────────────────────────────────────────────

def _parse_pdf(file_bytes: bytes) -> str:
    """Parse PDF using pdfplumber → pypdf → PyPDF2 fallback chain."""
    text = ""

    # Try pdfplumber first
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
            text = "\n".join(pages).strip()
        if len(text) > 100:
            return text
    except Exception as e:
        print(f"[Parser] pdfplumber failed: {e}")

    # Try pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
        if len(text) > 100:
            return text
    except Exception as e:
        print(f"[Parser] pypdf failed: {e}")

    # Try PyPDF2
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
        return text
    except Exception as e:
        print(f"[Parser] PyPDF2 failed: {e}")

    return ""


def _parse_docx(file_bytes: bytes) -> str:
    """Parse DOCX using python-docx."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        print(f"[Parser] DOCX parse failed: {e}")
        return ""


# ── Public API ────────────────────────────────────────────────────────────────

def parse_cv_file(
    filename: str,
    file_bytes: bytes,
    existing_hashes: set,
    source_category: Optional[str] = None,
) -> Optional[dict]:
    """
    Parse a single CV file and return structured fields.
    Returns None if duplicate or unparseable.
    """
    fname_lower = filename.lower()

    # Extract raw text
    if fname_lower.endswith(".pdf"):
        text = _parse_pdf(file_bytes)
    elif fname_lower.endswith(".docx"):
        text = _parse_docx(file_bytes)
    elif fname_lower.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="ignore")
    else:
        print(f"[Parser] Unsupported file type: {filename}")
        return None

    if len(text.strip()) < 50:
        print(f"[Parser] Empty or too short: {filename}")
        return None

    # Deduplication
    cv_hash = _hash_cv(text)
    if cv_hash in existing_hashes:
        print(f"[Parser] Duplicate skipped: {filename}")
        return None

    existing_hashes.add(cv_hash)

    fields = _extract_fields(text, source_category)
    fields["cv_hash"] = cv_hash
    fields["source_file"] = filename

    print(f"[Parser] Parsed: {fields.get('name', 'Unknown')} | {fields.get('current_title', 'N/A')} | {fields.get('years_experience', 0)}y | Skills: {fields.get('skills', '')[:60]}")
    return fields


def parse_zip_file(
    file_bytes: bytes,
    existing_hashes: set,
    source_category: Optional[str] = None,
) -> list:
    """Extract and parse all CV files from a ZIP archive."""
    import zipfile
    results = []
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            for name in zf.namelist():
                if name.startswith("__MACOSX") or name.startswith("."):
                    continue
                if any(name.lower().endswith(ext) for ext in [".pdf", ".docx", ".txt"]):
                    try:
                        data = zf.read(name)
                        basename = os.path.basename(name)
                        result = parse_cv_file(basename, data, existing_hashes, source_category)
                        if result:
                            results.append(result)
                    except Exception as e:
                        print(f"[Parser] ZIP entry error {name}: {e}")
    except Exception as e:
        print(f"[Parser] ZIP open error: {e}")
    return results


def parse_kaggle_csv_row(row: dict) -> Optional[dict]:
    """Parse a single row from the Kaggle Resume Dataset CSV."""
    text = row.get("Resume_str", "")
    if not text or len(text.strip()) < 50:
        return None
    category = row.get("Category", None)
    fields = _extract_fields(text, category)
    fields["cv_hash"] = _hash_cv(text)
    fields["source_file"] = "csv_import"
    return fields
