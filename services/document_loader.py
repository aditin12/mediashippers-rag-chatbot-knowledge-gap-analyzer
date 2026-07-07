import json
import yaml
from pathlib import Path
from docx import Document as DocxDocument
import pdfplumber
from bs4 import BeautifulSoup


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    ext  = path.suffix.lower()

    if ext == ".docx":
        doc = DocxDocument(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif ext == ".pdf":
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return text

    elif ext == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    elif ext == ".json":
        return json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2)

    elif ext == ".yaml":
        return yaml.dump(yaml.safe_load(path.read_text(encoding="utf-8")), default_flow_style=False)

    elif ext == ".html":
        return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser").get_text(separator="\n")

    return ""
