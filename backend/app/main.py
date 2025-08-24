import os
import io
import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

from pypdf import PdfReader

from .prompts import build_requirements_prompt, CRITERIA
from .scoring import compute_weighted_scores, normalize_score

# --- ENV ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("MODEL", "recruiter-gemma3:270m")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./storage/chroma")
SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:///./storage/app.db")

os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs("./storage", exist_ok=True)

# --- DB ---
Base = declarative_base()

class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    overall_score = Column(Float)
    details_json = Column(Text)  # JSON string with per-criterion results & comments
    resume_text = Column(Text)

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- LLM + Embeddings ---
llm = ChatOllama(model=MODEL, base_url=OLLAMA_HOST, temperature=0.2, num_ctx=32768)
embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_HOST)

# Vector store (per candidate namespace using collection_name)
def new_vectorstore(collection_name: str):
    return Chroma(
        collection_name=collection_name,
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
    )

# --- FastAPI ---
app = FastAPI(title="RAG Resume Shortlister", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL, "embed_model": EMBED_MODEL}

def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        t = page.extract_text() or ""
        text_parts.append(t)
    return "\n".join(text_parts)

def chunk_and_index(candidate_id: str, resume_text: str) -> int:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=120, length_function=len
    )
    docs = splitter.create_documents([resume_text])
    vs = new_vectorstore(collection_name=f"cand_{candidate_id}")
    vs.add_documents(docs)
    vs.persist()
    return len(docs)

def rag_query(candidate_id: str, query: str, k: int = 6) -> str:
    vs = new_vectorstore(collection_name=f"cand_{candidate_id}")
    docs = vs.similarity_search(query, k=k)
    context = "\n\n".join([d.page_content for d in docs])
    return context

@app.post("/api/upload")
async def upload_resume(file: UploadFile = File(...)):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Please upload a PDF.")
    data = await file.read()
    text = extract_text_from_pdf(data)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
    candidate_id = str(uuid.uuid4())
    num_chunks = chunk_and_index(candidate_id, text)
    return {"candidate_id": candidate_id, "chunks": num_chunks, "characters": len(text)}

@app.post("/api/evaluate")
async def evaluate_candidate(candidate_id: str = Form(...)):
    # Retrieve resume text back out of vector store context for persistence (optional best-effort)
    # Chroma doesn't store original doc text centrally, so the pipeline accepts resume text from a re-query.
    # We'll build a synthetic "resume_text" via top-k retrieval across generic queries.
    generic_queries = [
        "work experience and roles",
        "education and degrees",
        "programming languages and frameworks",
        "cloud and databases",
        "projects and achievements"
    ]
    resume_slices = []
    for q in generic_queries:
        resume_slices.append(rag_query(candidate_id, q, k=6))
    resume_text = "\n\n".join(resume_slices)

    # Build prompts for each requirement
    req_prompts = build_requirements_prompt()

    per_criterion: List[Dict[str, Any]] = []
    for crit in CRITERIA:
        # Retrieve focused context for this criterion
        context = rag_query(candidate_id, crit["query"], k=8)
        system_instructions = (
            "Evaluate the candidate ONLY using the provided <CONTEXT>. "
            "Return compact JSON: {criterion, score_percent (0-100), rationale, alternate_considerations}. "
            "Use conservative scoring. If evidence is missing, score low and suggest alternates."
        )
        user_prompt = f"""<CONTEXT>
{context}
</CONTEXT>

<REQUIREMENT>
{crit["requirement"]}
</REQUIREMENT>

Respond with JSON only.
"""
        # LLM call
        resp = llm.invoke([
            {"role":"system","content":system_instructions},
            {"role":"user","content":user_prompt}
        ])
        try:
            data = json.loads(resp.content.strip().strip("`").strip())
        except Exception:
            # Fallback parse: try to extract JSON substring
            txt = resp.content
            start = txt.find("{")
            end = txt.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    data = json.loads(txt[start:end+1])
                except Exception:
                    data = {
                        "criterion": crit["name"],
                        "score_percent": 0,
                        "rationale": "Could not parse model output.",
                        "alternate_considerations": []
                    }
            else:
                data = {
                    "criterion": crit["name"],
                    "score_percent": 0,
                    "rationale": "No JSON found in model output.",
                    "alternate_considerations": []
                }
        # Normalize and attach name
        data["criterion"] = crit["name"]
        data["score_percent"] = normalize_score(data.get("score_percent", 0))
        per_criterion.append(data)

    overall = compute_weighted_scores(per_criterion)

    # Persist
    db = SessionLocal()
    try:
        result = Result(
            candidate_id=candidate_id,
            overall_score=overall["overall_percent"],
            details_json=json.dumps({"per_criterion": per_criterion, "weights": overall["weights"]}),
            resume_text=resume_text[:200000],  # keep DB reasonable
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        rid = result.id
    finally:
        db.close()

    return {
        "result_id": rid,
        "candidate_id": candidate_id,
        "overall_percent": overall["overall_percent"],
        "per_criterion": per_criterion,
        "weights": overall["weights"],
        "summary": overall["summary"]
    }

@app.get("/api/results")
def list_results():
    db = SessionLocal()
    try:
        rows = db.query(Result).order_by(Result.created_at.desc()).limit(100).all()
        out = []
        for r in rows:
            out.append({
                "id": r.id,
                "candidate_id": r.candidate_id,
                "created_at": r.created_at.isoformat(),
                "overall_score": r.overall_score,
            })
        return out
    finally:
        db.close()

@app.get("/api/results/{result_id}")
def get_result(result_id: int):
    db = SessionLocal()
    try:
        r = db.get(Result, result_id)
        if not r:
            raise HTTPException(404, "Result not found")
        return {
            "id": r.id,
            "candidate_id": r.candidate_id,
            "created_at": r.created_at.isoformat(),
            "overall_score": r.overall_score,
            "details": json.loads(r.details_json),
        }
    finally:
        db.close()
