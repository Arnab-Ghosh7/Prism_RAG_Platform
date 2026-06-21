import json, time, hashlib
from typing import Dict, Optional, List
from openai import AsyncOpenAI
from pydantic import BaseModel
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

class PrismEngine:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Run in mock mode if API key is not set or is the placeholder value
        self.mock_mode = (not api_key) or api_key == "sk-..." or api_key == "" or "placeholder" in api_key.lower()
        if not self.mock_mode:
            self.llm = AsyncOpenAI(api_key=api_key)
        else:
            self.llm = None
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
        else:
            gen_prompt = f"""Answer the question based on the provided context. If the context doesn't contain the answer, say so.
            Context: {context}
            Question: {query}
            Respond in JSON: {{{{"answer": "...", "raw_confidence": 0.0-1.0, "reasoning": "...", "domain": "..."}}}}"""
            
            resp = await self.llm.chat.completions.create(
                model="gpt-4", messages=[{"role": "user", "content": gen_prompt}], temperature=0.1
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
            "calibration_error": round(self.calibration.expected_calibration_error(), 3)
        }

    def feedback(self, interaction_id: str, accuracy: float):
        if interaction_id in self.interactions:
            i = self.interactions[interaction_id]
            self.calibration.record(i["adjusted_confidence"], accuracy)
            self.cognitive_map.update(i["domain"], "general", i["adjusted_confidence"], accuracy)
            self.failure_miner.record(i["domain"], "general", i["adjusted_confidence"], accuracy)
            
    def status(self):
        return {
            "calibration_curve": self.calibration.get_calibration_curve(),
            "cognitive_map": self.cognitive_map.get_summary(),
            "vulnerabilities": self.failure_miner.get_vulnerability_report()
        }
