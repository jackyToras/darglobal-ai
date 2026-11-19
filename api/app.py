import time
import os
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from core.models import ChatRequest, ChatResponse, FilterParams
from core.session_manager import session_manager
from core.guardrails import guardrails_engine
from core.search_engine import search_engine
from core.openrouter_client import openrouter_client

app = FastAPI(title="DarGlobal & Wasalt AI Concierge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("frontend", exist_ok=True)
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    html_path = os.path.join("frontend", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>DarGlobal & Wasalt Real Estate AI Concierge API Active</h1>"

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "properties_indexed": len(search_engine.properties),
        "active_tenants": session_manager.active_tenant_count(),
        "openrouter_configured": bool(openrouter_client.api_key)
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, x_session_id: Optional[str] = Header(None)):
    start_time = time.time()
    
    session_id = payload.session_id or x_session_id
    tenant = session_manager.get_session(session_id)
    session_id = tenant.session_id

    raw_message = payload.message.strip()
    if not raw_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    sanitized_message = guardrails_engine.sanitize_input(raw_message)
    passed, guard_reply, guard_status = guardrails_engine.evaluate_input(sanitized_message)

    if not passed:
        tenant.add_message("user", sanitized_message)
        tenant.add_message("assistant", guard_reply)
        tenant.add_chunk(sanitized_message, metadata={"role": "user", "blocked": True})
        latency = (time.time() - start_time) * 1000
        return ChatResponse(
            reply=guard_reply,
            session_id=session_id,
            model_used="guardrails-filter",
            properties=[],
            latency_ms=round(latency, 2),
            cached=False,
            guardrail_status=guard_status
        )

    tenant.add_chunk(sanitized_message, metadata={"role": "user", "blocked": False})
    tenant_chunks = session_manager.get_user_chunks_only(session_id)
    
    matched_properties = search_engine.search(
        query=sanitized_message,
        top_k=3,
        explicit_filters=payload.filters,
        tenant_chunks=tenant_chunks
    )

    history = tenant.get_recent_messages(limit=6)
    reply_text, model_used, was_cached = openrouter_client.generate_response(
        user_query=sanitized_message,
        properties=matched_properties,
        history=history
    )

    titles = [p.get("title", "") for p in matched_properties]
    final_reply = guardrails_engine.verify_grounding(reply_text, titles)

    tenant.add_message("user", sanitized_message)
    tenant.add_message("assistant", final_reply)
    tenant.add_chunk(final_reply[:200], metadata={"role": "assistant"})

    latency = (time.time() - start_time) * 1000

    return ChatResponse(
        reply=final_reply,
        session_id=session_id,
        model_used=model_used,
        properties=matched_properties,
        latency_ms=round(latency, 2),
        cached=was_cached,
        guardrail_status="passed"
    )

@app.get("/api/properties")
async def list_properties(
    city: Optional[str] = None,
    platform: Optional[str] = None,
    property_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    bedrooms: Optional[int] = None,
    limit: int = 20
):
    results = search_engine.properties
    if platform:
        results = [p for p in results if p.get("platform", "").lower() == platform.lower()]
    if city:
        results = [p for p in results if city.lower() in p.get("city", "").lower()]
    if property_type:
        results = [p for p in results if property_type.lower() in p.get("property_type", "").lower()]
    if min_price is not None:
        results = [p for p in results if p.get("price_sar", 0.0) >= min_price]
    if max_price is not None:
        results = [p for p in results if p.get("price_sar", 0.0) <= max_price]
    if bedrooms is not None:
        results = [p for p in results if p.get("bedrooms") == bedrooms]
    return {"count": len(results), "properties": results[:limit]}

@app.post("/api/session/clear")
async def clear_session(payload: Dict[str, str]):
    sid = payload.get("session_id", "")
    success = session_manager.clear_session(sid)
    return {"status": "cleared" if success else "not_found", "session_id": sid}
