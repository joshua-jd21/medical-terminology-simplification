import unicodedata
from pypdf import PdfReader
from io import BytesIO


def extract_document_text(file_content, filename):

    filename = filename.lower()

    # Extract text from PDF
    if filename.endswith(".pdf"):

        reader = PdfReader(BytesIO(file_content))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages)

    # Extract text from TXT
    elif filename.endswith(".txt"):

        text = file_content.decode("utf-8-sig")

    # Unsupported file format
    else:

        raise ValueError(
            "Only PDF and TXT files are supported."
        )

    # Decompose typographic ligatures (ﬁ -> fi, ﬂ -> fl, ﬀ -> ff)
    text = unicodedata.normalize("NFKC", text)

    # Check whether text was extracted
    if not text.strip():

        raise ValueError(
            "No readable text found in the document."
        )

    return text.strip()