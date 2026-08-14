from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prism_engine import PrismEngine, PRISMQuery, PRISMFeedback, PRISMIngest
import os
from dotenv import load_dotenv

load_dotenv()

allowed_origins = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]

app = FastAPI(
    title="PRISM Metacognitive RAG API",
    version="1.0.0",
    description="Retrieval-augmented generation with confidence calibration and feedback-driven diagnostics.",
    openapi_tags=[
        {"name": "system", "description": "Service health and runtime status."},
        {"name": "rag", "description": "Knowledge ingestion and retrieval-augmented queries."},
        {"name": "feedback", "description": "Response-quality feedback used for calibration."},
    ],
)

app.add_middleware(
    CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

engine = PrismEngine(
    openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
    anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
)

@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "provider": engine.provider, "model": engine.model or "mock"}

@app.post("/api/query", tags=["rag"])
async def query_prism(data: PRISMQuery):
    return await engine.process(data.query)

@app.post("/api/feedback", tags=["feedback"])
async def give_feedback(data: PRISMFeedback):
    if data.interaction_id not in engine.interactions:
        raise HTTPException(status_code=404, detail="Interaction not found")

    engine.feedback(data.interaction_id, data.accuracy)
    return {"status": "recorded"}

@app.post("/api/ingest", tags=["rag"])
async def ingest_data(data: PRISMIngest):
    engine.rag.ingest(data.texts, data.metadatas)
    return {"status": "ingested", "chunks": len(data.texts)}

@app.get("/api/status", tags=["system"])
async def get_status():
    return engine.status()
