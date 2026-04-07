from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from model_behavior import BehaviorInput, BehaviorModel
from rag_engine import RAGEngine


app = FastAPI(
    title="AI E-commerce Service",
    version="1.0.0",
    description="Behavior segmentation and RAG chatbot for bookstore demos.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

behavior_model = BehaviorModel()
rag_engine = RAGEngine()


class BehaviorPayload(BaseModel):
    clicks: float = Field(ge=0)
    add_to_cart: float = Field(ge=0)
    total_spend: float = Field(ge=0)
    session_duration: float = Field(ge=0)

    def to_input(self) -> BehaviorInput:
        return BehaviorInput(
            clicks=self.clicks,
            add_to_cart=self.add_to_cart,
            total_spend=self.total_spend,
            session_duration=self.session_duration,
        )


class AnalyzeBehaviorResponse(BaseModel):
    segment: str
    confidence: float
    probabilities: Dict[str, float]
    features: Dict[str, float]


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    behavior: Optional[BehaviorPayload] = None
    top_k: int = Field(default=4, ge=1, le=8)


class SourceReference(BaseModel):
    source: str
    chunk_index: int
    score: float
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    behavior_analysis: Optional[AnalyzeBehaviorResponse] = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze-behavior", response_model=AnalyzeBehaviorResponse)
def analyze_behavior(payload: BehaviorPayload) -> Dict[str, Any]:
    return behavior_model.predict(payload.to_input())


@app.post("/chat-tu-van", response_model=ChatResponse)
@app.post("/chat-tuvấn", response_model=ChatResponse)
def chat_tuvan(payload: ChatRequest) -> Dict[str, Any]:
    behavior_analysis = None
    if payload.behavior is not None:
        behavior_analysis = behavior_model.predict(payload.behavior.to_input())

    rag_result = rag_engine.answer_question(
        question=payload.question,
        behavior_context=behavior_analysis,
        top_k=payload.top_k,
    )

    return {
        "answer": rag_result["answer"],
        "sources": rag_result["sources"],
        "behavior_analysis": behavior_analysis,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)