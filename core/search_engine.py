import json
import math
import os
import re
from typing import List, Dict, Any, Optional

STOPWORDS = {
    "in", "at", "of", "for", "the", "a", "an", "is", "to", "and", "or", 
    "by", "on", "with", "what", "which", "where", "how", "tell", "show", 
    "me", "does", "have", "can", "you", "give", "about", "are", "from"
}

UNSUPPORTED_LOCATIONS = [
    "india", "delhi", "mumbai", "bangalore", "gurgaon", "noida", "hyderabad", "chennai", "kolkata",
    "california", "usa", "america", "canada", "australia", "germany", "france", "italy", "japan",
    "new york", "los angeles", "miami", "florida", "texas", "chicago"
]

SUPPORTED_CITIES = [
    "dubai", "riyadh", "jeddah", "dammam", "makkah", "madina", "muscat", "marbella", "doha", "london",
    "benahavis", "qetaifan", "sedra", "khobar"
]

class HybridSearchEngine:
    def __init__(self, data_path: str = "data/properties.json"):
        self.data_path = data_path
        self.properties: List[Dict[str, Any]] = []
        self.corpus_tokens: List[List[str]] = []
        self.doc_freq: Dict[str, int] = {}
        self.avg_doc_len: float = 0.0
        self.k1: float = 1.5
        self.b: float = 0.75
        self.min_relevance_score: float = 0.85
        self.load_data()

    def tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return [w for w in cleaned.split() if len(w) > 2 and w not in STOPWORDS]

    def load_data(self):
        if not os.path.exists(self.data_path):
            self.properties = []
            return
        with open(self.data_path, "r", encoding="utf-8") as f:
            self.properties = json.load(f)

        total_len = 0
        self.corpus_tokens = []
        self.doc_freq = {}

        for p in self.properties:
            doc_text = f"{p.get('title', '')} {p.get('project_name', '')} {p.get('brand_partner', '')} {p.get('city', '')} {p.get('country', '')} {p.get('district', '')} {p.get('property_type', '')} {p.get('description', '')} {' '.join(p.get('amenities', []))}"
            tokens = self.tokenize(doc_text)
            self.corpus_tokens.append(tokens)
            total_len += len(tokens)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.doc_freq[t] = self.doc_freq.get(t, 0) + 1

        self.avg_doc_len = (total_len / len(self.properties)) if self.properties else 1.0

    def parse_query_constraints(self, query: str) -> Dict[str, Any]:
        lowered = query.lower()
        constraints = {}

        if "darglobal" in lowered or "dar global" in lowered:
            constraints["platform"] = "DarGlobal"
        elif "wasalt" in lowered:
            constraints["platform"] = "Wasalt"

        cities = ["dubai", "riyadh", "jeddah", "dammam", "makkah", "madina", "muscat", "marbella", "doha", "london"]
        for c in cities:
            if c in lowered:
                constraints["city"] = c.capitalize()
                break

        price_matches = re.findall(r"(?:under|below|less than|max|budget)\s*([\d\.,]+)\s*(?:m|million|k)?", lowered)
        if price_matches:
            raw_val = price_matches[0].replace(",", "")
            try:
                num = float(raw_val)
                if "million" in lowered or "m" in lowered and num < 100:
                    num = num * 1000000
                elif "k" in lowered and num < 1000:
                    num = num * 1000
                constraints["max_price"] = num
            except:
                pass

        bed_match = re.search(r"(\d+)\s*(?:bed|bedroom|bhk)", lowered)
        if bed_match:
            try:
                constraints["bedrooms"] = int(bed_match.group(1))
            except:
                pass

        if "rent" in lowered and "sale" not in lowered:
            constraints["listing_type"] = "rent"
        elif "sale" in lowered or "buy" in lowered:
            constraints["listing_type"] = "sale"

        return constraints

    def score_bm25(self, query_tokens: List[str], doc_idx: int) -> float:
        score = 0.0
        doc_tokens = self.corpus_tokens[doc_idx]
        doc_len = len(doc_tokens)
        doc_counts: Dict[str, int] = {}
        for t in doc_tokens:
            doc_counts[t] = doc_counts.get(t, 0) + 1

        n_docs = len(self.properties)

        for q in query_tokens:
            if q not in self.doc_freq:
                continue
            df = self.doc_freq[q]
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            tf = doc_counts.get(q, 0)
            numerator = tf * (self.k1 + 1.0)
            denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
            score += idf * (numerator / (denominator + 1e-9))
        return score

    def search(self, query: str, top_k: int = 4, explicit_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        lowered = query.lower()
        for loc in UNSUPPORTED_LOCATIONS:
            if re.search(r"\b" + re.escape(loc) + r"\b", lowered):
                if not any(re.search(r"\b" + re.escape(c) + r"\b", lowered) for c in SUPPORTED_CITIES):
                    return []

        parsed = self.parse_query_constraints(query)
        if explicit_filters:
            parsed.update({k: v for k, v in explicit_filters.items() if v is not None})

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        candidates = []

        for idx, p in enumerate(self.properties):
            if parsed.get("platform"):
                if p.get("platform", "").lower() != parsed["platform"].lower():
                    continue

            if parsed.get("city"):
                if parsed["city"].lower() not in p.get("city", "").lower():
                    continue

            if parsed.get("max_price"):
                if p.get("price_sar", 0.0) > (parsed["max_price"] * 1.15):
                    continue

            if parsed.get("bedrooms"):
                if p.get("bedrooms") is not None and p.get("bedrooms") < parsed["bedrooms"]:
                    continue

            if parsed.get("listing_type"):
                if p.get("listing_type", "").lower() != parsed["listing_type"].lower():
                    continue

            bm25 = self.score_bm25(query_tokens, idx)
            if bm25 >= self.min_relevance_score:
                candidates.append((bm25, p))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in candidates[:top_k]]

search_engine = HybridSearchEngine()
