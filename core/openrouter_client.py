import os
import json
import time
import urllib.request
import urllib.error
import re
from typing import List, Dict, Any, Tuple, Optional

def load_env_file(filepath: str = ".env"):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k_str = k.strip()
                    if k_str not in os.environ:
                        os.environ[k_str] = v.strip()

load_env_file()

FREE_MODELS = [
    "openrouter/free",
    "nvidia/nemotron-3.5-lightning:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "baidu/ernie-5.5-flash-preview:free"
]

SYSTEM_PROMPT = """You are the Senior Real Estate AI Advisor representing DarGlobal and Wasalt.
DarGlobal develops elite international branded residences in Dubai, Oman, Qatar, Spain, and Saudi Arabia in partnership with brands like Pagani, Automobili Lamborghini, Missoni, Elie Saab, and Trump Organization.
Wasalt is Saudi Arabia's premier proptech marketplace for residential villas, apartments, lands, and investments across Riyadh, Jeddah, Dammam, and Makkah.

Your mandate:
1. Provide accurate, professional, and strictly grounded real estate guidance.
2. Only recommend properties present in the verified context provided below.
3. If no matching properties exist in the verified context, or if the user asks about properties, brands, or locations outside our verified catalog (such as Ferrari, DLF, Bandra, Tokyo, etc.), you MUST explicitly state that the requested brand, property, or location is not part of the verified DarGlobal and Wasalt catalog. Do NOT substitute or recommend unrelated properties.
4. Format responses cleanly with bold titles, concise bullet points, and pricing figures.
5. If answering in Arabic, maintain a polished, fluent professional tone.
"""

class SemanticLRUCache:
    def __init__(self, max_size: int = 500, ttl_seconds: int = 21600):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.entries: Dict[str, Dict[str, Any]] = {}

    def _normalize(self, text: str) -> str:
        return " ".join(re.findall(r"[a-zA-Z0-9\u0600-\u06FF]+", text.lower()))

    def get(self, query: str, has_properties: Optional[bool] = None) -> Optional[Tuple[str, str]]:
        norm_key = self._normalize(query)
        now = time.time()

        entry = self.entries.get(norm_key)
        if entry:
            if now - entry["timestamp"] > self.ttl:
                del self.entries[norm_key]
                return None

            if has_properties is not None:
                is_boundary = entry.get("model") == "grounded-boundary-filter"
                if has_properties and is_boundary:
                    return None
                if not has_properties and not is_boundary:
                    return None

            return (entry["reply"], entry["model"])
        return None

    def put(self, query: str, reply: str, model: str):
        norm_key = self._normalize(query)
        if len(self.entries) >= self.max_size:
            oldest_key = min(self.entries.keys(), key=lambda k: self.entries[k]["timestamp"])
            del self.entries[oldest_key]

        self.entries[norm_key] = {
            "reply": reply,
            "model": model,
            "timestamp": time.time()
        }

class OpenRouterClient:
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.cache = SemanticLRUCache(max_size=500, ttl_seconds=21600)
        self.models = self._fetch_active_models()

    def _fetch_active_models(self) -> List[str]:
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/models")
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode("utf-8"))
                active_free = [m["id"] for m in data.get("data", []) if ":free" in m.get("id", "")]
                if active_free:
                    return ["openrouter/free"] + active_free[:4]
        except:
            pass
        return FREE_MODELS

    def _format_context(self, properties: List[Dict[str, Any]]) -> str:
        if not properties:
            return "NO MATCHING PROPERTIES FOUND IN VERIFIED PORTFOLIO."
        lines = []
        for p in properties:
            lines.append(
                f"- [{p.get('platform')}] {p.get('title')} | City: {p.get('city')}, {p.get('country')} | "
                f"Price: {p.get('price_sar'):,.0f} SAR | Type: {p.get('property_type')} | "
                f"Beds: {p.get('bedrooms')} | Status: {p.get('status')} | URL: {p.get('official_url')}"
            )
        return "\n".join(lines)

    def _generate_offline_advisory(self, user_query: str, properties: List[Dict[str, Any]]) -> str:
        if not properties:
            lowered = user_query.lower()
            tokens = set(re.findall(r"[a-zA-Z\u0600-\u06FF]+", lowered))
            greeting_words = {"hi", "hello", "hey", "marhaba", "salam", "morning", "evening", "help"}
            if tokens.intersection(greeting_words) or "who are you" in lowered:
                return "Welcome to the DarGlobal & Wasalt Real Estate Concierge. I am your AI advisor for luxury international developments (Dubai, Oman, Qatar, Spain, UK) and Saudi Arabian residential properties (Riyadh, Jeddah, Dammam). How may I assist your property search or investment today?"
            return f"I cannot find any properties matching '{user_query}' in our verified portfolio. DarGlobal and Wasalt specialize exclusively in luxury international branded developments (Dubai, Oman, Qatar, Spain, UK) and residential/commercial real estate in Saudi Arabia (Riyadh, Jeddah, Dammam). The requested brand, project, or location is not part of our verified catalog. Please let me know if you would like to explore luxury residences or investment assets within our official regions."

        lines = ["Here are the premier verified properties matching your criteria from DarGlobal and Wasalt:\n"]
        for p in properties:
            price_str = f"{p.get('price_sar', 0):,.0f} SAR" if p.get('price_sar', 0) > 0 else "Price on Application"
            brand = f" (Brand: {p.get('brand_partner')})" if p.get('brand_partner') and p.get('brand_partner') != "None" else ""
            lines.append(f"### **{p.get('title')}**{brand}")
            lines.append(f"- **Platform & Developer**: {p.get('platform')} ({p.get('developer')})")
            lines.append(f"- **Location**: {p.get('district')}, {p.get('city')}, {p.get('country')}")
            lines.append(f"- **Specifications**: {p.get('bedrooms')} Bedrooms | {p.get('property_type')} | {p.get('area_sqm')} SQM")
            lines.append(f"- **Investment / Price**: {price_str}")
            lines.append(f"- **Highlights**: {p.get('description', '')[:200]}...")
            lines.append(f"- **Official Page**: [View Listing Details]({p.get('official_url')})\n")

        lines.append("Would you like to explore financing options, schedule a private viewing, or compare expected rental yields across these assets?")
        return "\n".join(lines)

    def generate_response(self, user_query: str, properties: List[Dict[str, Any]], history: List[Dict[str, str]] = None, tenant_chunks: List[Dict[str, Any]] = None) -> Tuple[str, str, bool]:
        has_props = bool(properties)
        cached_result = self.cache.get(user_query, has_properties=has_props)
        if cached_result:
            reply, model_name = cached_result
            return reply, model_name, True

        if not properties:
            reply = self._generate_offline_advisory(user_query, [])
            self.cache.put(user_query, reply, "grounded-boundary-filter")
            return reply, "grounded-boundary-filter", False

        if not self.api_key:
            reply = self._generate_offline_advisory(user_query, properties)
            self.cache.put(user_query, reply, "offline-grounded-engine")
            return reply, "offline-grounded-engine", False

        context_str = self._format_context(properties)
        system_text = f"{SYSTEM_PROMPT}\n\nVERIFIED PROPERTY CONTEXT:\n{context_str}"
        
        if tenant_chunks:
            chunk_texts = [f"- {c.get('text', '')}" for c in tenant_chunks[-3:]]
            system_text += f"\n\nTENANT PRIVATE MEMORY CHUNKS (ISOLATED TO CURRENT USER):\n" + "\n".join(chunk_texts)

        messages = [
            {"role": "system", "content": system_text}
        ]

        if history:
            for h in history[-4:]:
                messages.append({"role": h["role"], "content": h["content"]})

        messages.append({"role": "user", "content": user_query})

        models_to_try = self.models or FREE_MODELS

        for model in models_to_try:
            payload = {
                "model": model,
                "models": models_to_try,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 800
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://darglobal.co.uk",
                "X-Title": "DarGlobal Wasalt AI Concierge"
            }

            req = urllib.request.Request(
                self.base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=14) as resp:
                    res_body = json.loads(resp.read().decode("utf-8"))
                    choices = res_body.get("choices", [])
                    if choices and "message" in choices[0]:
                        reply = choices[0]["message"]["content"]
                        actual_model = res_body.get("model", model)
                        self.cache.put(user_query, reply, actual_model)
                        return reply, actual_model, False
            except Exception as e:
                time.sleep(0.5)
                continue

        reply = self._generate_offline_advisory(user_query, properties)
        self.cache.put(user_query, reply, "offline-fallback-engine")
        return reply, "offline-fallback-engine", False

openrouter_client = OpenRouterClient()
