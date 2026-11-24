# MediSimplify AI

## Project Overview

MediSimplify AI is an NLP-based Medical Terminology
Simplification System that helps users understand complex
medical terminology in healthcare documents.

## Objectives

- Identify complex medical terminology using regular
  expressions, tokenization and morphological normalization.
- Map medical terms to simple explanations using a
  predefined medical dictionary.
- Display simplified medical documents through a
  user-friendly interface.

## Features

- Medical text simplification
- PDF and TXT document upload
- Medical terminology identification
- Tokenization and lemmatization
- Medical dictionary-based explanations
- Simplified PDF report download
- User-friendly web interface
- No external APIs or API keys required

## Technologies Used

- Python
- FastAPI
- NLTK
- HTML, CSS and JavaScript
- JSON
- PyPDF
- ReportLab

## Installation

Python 3 is required.

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

For Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Download the required NLTK resources:

```bash
python -m nltk.downloader wordnet omw-1.4
```

## Running the Project

Start the backend in Terminal 1:

```bash
python main.py
```

Start the frontend in Terminal 2 from the project folder:

```bash
python -m http.server 5500 --bind 127.0.0.1
```

Open the following address in your browser:

http://localhost:5500/index.html

## Example

Input:

The patient has hypertension and dyspnea.

Output:

The patient has hypertension (high blood pressure)
and dyspnea (difficulty breathing).

## Project Structure

- main.py - FastAPI backend
- index.html - Frontend interface
- terminology_simplifier.py - NLP processing
- medical_dictionary.json - Medical terminology dictionary
- document_reader.py - PDF and TXT text extraction
- simplified_pdf_generator.py - PDF report generation
- requirements.txt - Python dependencies
- .gitignore - Git exclusion rules

## Sustainable Development Goal

SDG 3: Good Health and Well-being

The project aims to improve health literacy by making
medical information easier to understand.

## Limitations

- Simplification is limited to the predefined dictionary.
- Scanned PDFs requiring OCR are not supported.
- Maximum document upload size is 5 MB.
- The system does not provide medical diagnosis or treatment.

## Disclaimer

This project is developed for educational and informational
purposes. It is not a substitute for professional medical advice.
