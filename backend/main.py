from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prism_engine import PrismEngine, PRISMQuery, PRISMFeedback, PRISMIngest
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PRISM Metacognitive RAG API")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

engine = PrismEngine(
    openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
    anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
)

@app.post("/api/query")
async def query_prism(data: PRISMQuery):
    return await engine.process(data.query)

@app.post("/api/feedback")
async def give_feedback(data: PRISMFeedback):
    engine.feedback(data.interaction_id, data.accuracy)
    return {"status": "recorded"}

@app.post("/api/ingest")
async def ingest_data(data: PRISMIngest):
    engine.rag.ingest(data.texts, data.metadatas)
    return {"status": "ingested", "chunks": len(data.texts)}

@app.get("/api/status")
async def get_status():
    return engine.status()
