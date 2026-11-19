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
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "mistralai/mistral-small-24b-instruct-2501:free",
    "openrouter/free"
]

SYSTEM_PROMPT = """You are the Senior Real Estate AI Advisor representing DarGlobal and Wasalt.
DarGlobal develops elite international branded residences in Dubai, Oman, Qatar, Spain, and Saudi Arabia in partnership with brands like Pagani, Automobili Lamborghini, Missoni, Elie Saab, and Trump Organization.
Wasalt is Saudi Arabia's premier proptech marketplace for residential villas, apartments, lands, and investments across Riyadh, Jeddah, Dammam, and Makkah.

Your mandate:
1. Provide accurate, professional, and strictly grounded real estate guidance.
2. Only recommend properties present in the verified context provided below.
3. If no matching properties exist in the verified context, or if the user asks about properties/locations outside our portfolio, you MUST explicitly state that the property is not in the verified DarGlobal and Wasalt catalog. Do NOT hallucinate or discuss unverified outside projects.
4. Format responses cleanly with bold titles, concise bullet points, and pricing figures.
5. If answering in Arabic, maintain a polished, fluent professional tone.
"""

class SemanticLRUCache:
    def __init__(self, max_size: int = 500, ttl_seconds: int = 21600):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.entries: Dict[str, Dict[str, Any]] = {}

    def _tokenize(self, text: str) -> set:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return {w for w in cleaned.split() if len(w) > 2}

    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def get(self, query: str) -> Optional[Tuple[str, str]]:
        now = time.time()
        q_tokens = self._tokenize(query)
        best_match = None
        best_score = 0.0

        for key, item in list(self.entries.items()):
            if now - item["timestamp"] > self.ttl:
                del self.entries[key]
                continue

            similarity = self._jaccard_similarity(q_tokens, item["tokens"])
            if similarity >= 0.70 and similarity > best_score:
                best_score = similarity
                best_match = (item["reply"], item["model"])

        if best_match:
            return best_match
        return None

    def put(self, query: str, reply: str, model: str):
        if len(self.entries) >= self.max_size:
            oldest_key = min(self.entries.keys(), key=lambda k: self.entries[k]["timestamp"])
            del self.entries[oldest_key]

        norm_key = " ".join(query.lower().strip().split())
        self.entries[norm_key] = {
            "reply": reply,
            "model": model,
            "tokens": self._tokenize(query),
            "timestamp": time.time()
        }

class OpenRouterClient:
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.cache = SemanticLRUCache(max_size=500, ttl_seconds=21600)

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
            return f"I cannot find any properties matching '{user_query}' in our verified portfolio. I exclusively provide information on DarGlobal's luxury branded residences (Dubai, Oman, Qatar, Spain, UK, Saudi Arabia) and Wasalt's Saudi marketplace. The requested property or location is not part of our verified catalog. Please feel free to ask about our official developments such as DG1 Living, DaVinci Pagani Tower, AIDA Oman, Tierra Viva, or residential properties across Riyadh and Jeddah."

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
        cached_result = self.cache.get(user_query)
        if cached_result:
            reply, model_name = cached_result
            return reply, model_name, True

        if not self.api_key or not properties:
            reply = self._generate_offline_advisory(user_query, properties)
            self.cache.put(user_query, reply, "offline-grounded-engine" if not properties else "offline-fallback-engine")
            return reply, "offline-grounded-engine" if not properties else "offline-fallback-engine", False

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

        for model in FREE_MODELS:
            payload = {
                "model": model,
                "models": FREE_MODELS,
                "messages": messages,
                "temperature": 0.4,
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
