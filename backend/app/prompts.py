from typing import List, Dict

# The explicit requisites (no LangGraph)
CRITERIA: List[Dict] = [
    {
        "name": "Degree & Experience (CS Master OR CS Bachelor + 2y)",
        "requirement": (
            "Candidate has either: (a) a Master's degree in Computer Science, OR "
            "(b) a Bachelor's degree in Computer Science PLUS at least 2 years of work experience."
        ),
        "query": "education, degree, master, bachelor, computer science, work experience duration"
    },
    {
        "name": "Python & OCR (>=5 years)",
        "requirement": "Candidate has 5+ years professional experience with Python AND OCR development (e.g., Tesseract, OpenCV, pytesseract, AWS Textract, Azure Computer Vision, Google Vision).",
        "query": "python experience years, OCR, pytesseract, tesseract, opencv, textract, google vision, azure computer vision"
    },
    {
        "name": "OOP Language: C++ or Java",
        "requirement": "Candidate has programming experience with object-oriented languages similar to Python such as C++ or Java.",
        "query": "C++, Java, object oriented, OOP, classes, interfaces"
    },
    {
        "name": "SQL & Cloud (Azure/AWS/GCP)",
        "requirement": "Candidate has direct experience with SQL and at least one major cloud (Azure, AWS, or GCP).",
        "query": "SQL, PostgreSQL, MySQL, T-SQL, BigQuery, Azure, AWS, GCP, cloud services"
    },
]

def build_requirements_prompt():
    # Kept for future expansion if we want to synthesize a natural language list
    return CRITERIA
