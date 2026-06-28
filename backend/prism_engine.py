import json, time, hashlib, logging
from typing import Dict, Optional, List
from pydantic import BaseModel

# LLM clients are optional — the engine falls back to a safe Mock Mode if the
# selected provider's SDK (or API key) is missing.
try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except Exception:
    ANTHROPIC_AVAILABLE = False

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

from rag_engine import RAGEngine
from calibration import CalibrationTracker
from failure_miner import FailurePatternMiner
from cognitive_map import CognitiveMap

class PRISMQuery(BaseModel):
    query: str

class PRISMFeedback(BaseModel):
    interaction_id: str
    accuracy: float

class PRISMIngest(BaseModel):
    texts: List[str]
    metadatas: List[Dict]

def _is_valid_key(key: Optional[str]) -> bool:
    """A key counts as real only if it's set and not a placeholder."""
    if not key:
        return False
    k = key.strip()
    if k in ("", "sk-...", "sk-ant-..."):
        return False
    return "placeholder" not in k.lower()


class PrismEngine:
    def __init__(self, openai_api_key: Optional[str] = None, anthropic_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key

        # Provider selection: Anthropic (Claude) is preferred when its key is
        # present, then OpenAI, otherwise a safe offline Mock Mode.
        self.provider = "mock"
        self.model = None
        self.llm = None

        if _is_valid_key(anthropic_api_key) and ANTHROPIC_AVAILABLE:
            self.provider = "anthropic"
            self.model = "claude-opus-4-8"
            self.llm = AsyncAnthropic(api_key=anthropic_api_key)
        elif _is_valid_key(anthropic_api_key) and not ANTHROPIC_AVAILABLE:
            logging.warning("ANTHROPIC_API_KEY set but the 'anthropic' package is not installed. "
                            "Run `pip install anthropic`. Falling back to Mock Mode.")
        elif _is_valid_key(openai_api_key) and OPENAI_AVAILABLE:
            self.provider = "openai"
            self.model = "gpt-4"
            self.llm = AsyncOpenAI(api_key=openai_api_key)
        elif _is_valid_key(openai_api_key) and not OPENAI_AVAILABLE:
            logging.warning("OPENAI_API_KEY set but the 'openai' package is not installed. "
                            "Falling back to Mock Mode.")

        self.mock_mode = self.provider == "mock"
        self.rag = RAGEngine()
        self.calibration = CalibrationTracker()
        self.failure_miner = FailurePatternMiner()
        self.cognitive_map = CognitiveMap()
        self.interactions = {}

    async def process(self, query: str) -> Dict:
        # 1. RAG RETRIEVAL
        rag_results = self.rag.retrieve(query)
        context = "\n".join(rag_results["documents"])
        rag_conf = rag_results["retrieval_confidence"]
        
        # 2. GENERATE WITH CONTEXT (OR MOCK GENERATION)
        if self.mock_mode:
            if rag_results["documents"]:
                doc_snippet = rag_results["documents"][0][:150]
                answer = f"[Mock Mode] Answer derived from retrieved context: \"{doc_snippet}...\""
                raw_c = 0.85
            else:
                answer = f"[Mock Mode] I do not have context to answer: \"{query}\". Please ingest some knowledge first."
                raw_c = 0.20
            gen = {
                "answer": answer,
                "raw_confidence": raw_c,
                "reasoning": "Generated in safe mock mode without OpenAI API key.",
                "domain": "general"
            }
        elif self.provider == "anthropic":
            gen_prompt = (
                "Answer the question based only on the provided context. "
                "If the context doesn't contain the answer, say so.\n\n"
                f"Context: {context}\n\n"
                f"Question: {query}\n\n"
                'Respond with ONLY a JSON object (no markdown, no prose) of the form: '
                '{"answer": "...", "raw_confidence": 0.0-1.0, "reasoning": "...", "domain": "..."}'
            )
            resp = await self.llm.messages.create(
                model=self.model,
                max_tokens=1024,
                system="You are a careful retrieval-augmented assistant. Always reply with a single valid JSON object and nothing else.",
                messages=[{"role": "user", "content": gen_prompt}],
            )
            raw_text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
            try:
                gen = json.loads(raw_text)
            except Exception:
                gen = {"answer": raw_text, "raw_confidence": 0.5, "reasoning": "Model did not return valid JSON.", "domain": "unknown"}

        else:  # openai
            gen_prompt = f"""Answer the question based on the provided context. If the context doesn't contain the answer, say so.
            Context: {context}
            Question: {query}
            Respond in JSON: {{{{"answer": "...", "raw_confidence": 0.0-1.0, "reasoning": "...", "domain": "..."}}}}"""

            resp = await self.llm.chat.completions.create(
                model=self.model, messages=[{"role": "user", "content": gen_prompt}], temperature=0.1
            )
            try:
                gen = json.loads(resp.choices[0].message.content)
            except:
                gen = {"answer": resp.choices[0].message.content, "raw_confidence": 0.5, "domain": "unknown"}

        # 3. METACOGNITIVE ADJUSTMENT (RAG-Aware)
        raw_c = gen.get("raw_confidence", 0.5)
        adjusted_c = raw_c * (0.5 + 0.5 * rag_conf) 
        
        # 4. PREDICT ACCURACY & CLASSIFY
        pred_acc = self.calibration.predict_accuracy(adjusted_c)
        soc = self.calibration.second_order_confidence(adjusted_c)
        
        quad = "KNOWN_KNOWN"
        if pred_acc < 0.6 and adjusted_c >= 0.6: quad = "UNKNOWN_KNOWN"
        elif pred_acc >= 0.6 and adjusted_c < 0.6: quad = "KNOWN_UNKNOWN"
        elif pred_acc < 0.6 and adjusted_c < 0.6: quad = "UNKNOWN_UNKNOWN"

        int_id = hashlib.md5(f"{query}{time.time()}".encode()).hexdigest()[:12]
        self.interactions[int_id] = {
            "query": query, "domain": gen.get("domain", "unknown"),
            "adjusted_confidence": adjusted_c, "quadrant": quad
        }

        return {
            "interaction_id": int_id,
            "answer": gen["answer"],
            "context_used": context[:500] + "..." if len(context) > 500 else context,
            "raw_confidence": round(raw_c, 3),
            "adjusted_confidence": round(adjusted_c, 3),
            "retrieval_confidence": round(rag_conf, 3),
            "predicted_accuracy": round(pred_acc, 3),
            "second_order_confidence": round(soc, 3),
            "cognitive_quadrant": quad,
            "calibration_error": round(self.calibration.expected_calibration_error(), 3),
            "provider": self.provider,
            "model": self.model or "mock"
        }

    def feedback(self, interaction_id: str, accuracy: float):
        if interaction_id in self.interactions:
            i = self.interactions[interaction_id]
            self.calibration.record(i["adjusted_confidence"], accuracy)
            self.cognitive_map.update(i["domain"], "general", i["adjusted_confidence"], accuracy)
            self.failure_miner.record(i["domain"], "general", i["adjusted_confidence"], accuracy)
            
    def status(self):
        return {
            "provider": self.provider,
            "model": self.model or "mock",
            "calibration_curve": self.calibration.get_calibration_curve(),
            "cognitive_map": self.cognitive_map.get_summary(),
            "vulnerabilities": self.failure_miner.get_vulnerability_report()
        }
