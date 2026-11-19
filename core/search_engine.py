import json
import math
import os
import re
from typing import List, Dict, Any, Optional, Set

STOPWORDS = {
    "in", "at", "of", "for", "the", "a", "an", "is", "to", "and", "or", 
    "by", "on", "with", "what", "which", "where", "how", "tell", "show", 
    "me", "does", "have", "can", "you", "give", "about", "are", "from",
    "i", "we", "my", "our", "would", "like", "want", "need", "any", "some",
    "this", "that", "these", "those", "all"
}

GENERIC_DESCRIPTORS = {
    "property", "properties", "real", "estate", "home", "homes", "house", "houses",
    "unit", "units", "residence", "residences", "residential", "commercial",
    "apartment", "apartments", "flat", "flats", "villa", "villas", "mansion", "mansions",
    "penthouse", "penthouses", "townhouse", "townhouses", "duplex", "studio", "land", "plot", "plots",
    "floor", "floors", "plan", "plans", "layout", "layouts", "building", "buildings",
    "sale", "rent", "buy", "lease", "price", "cost", "budget", "investment", "invest", "roi", "yield",
    "sar", "aed", "omr", "eur", "usd", "sqm", "sqft", "meter", "meters", "bedroom", "bedrooms",
    "bed", "beds", "bhk", "room", "rooms", "bathroom", "bathrooms", "bath", "baths",
    "best", "top", "good", "luxury", "luxurious", "ultra", "modern", "new", "ready", "offplan",
    "branded", "brand", "brands", "designer", "design", "designs",
    "view", "views", "facing", "sea", "water", "waterfront", "beach", "beachfront", "canal", "corniche",
    "available", "show", "tell", "give", "list", "recommend", "options", "details", "info", "find",
    "looking", "search", "explore", "under", "below", "above", "around", "near", "location", "place",
    "high", "low", "cheap", "expensive", "affordable", "family", "living"
}

PROPERTY_TYPES_MAP = {
    "apartment": ["apartment", "residential"],
    "apartments": ["apartment", "residential"],
    "flat": ["apartment", "residential"],
    "flats": ["apartment", "residential"],
    "villa": ["villa", "mansion"],
    "villas": ["villa", "mansion"],
    "mansion": ["mansion", "villa"],
    "mansions": ["mansion", "villa"],
    "penthouse": ["penthouse"],
    "penthouses": ["penthouse"],
    "floor": ["floor"],
    "floors": ["floor"],
    "townhouse": ["townhouse"],
    "townhouses": ["townhouse"],
    "land": ["land", "plot"],
    "plot": ["land", "plot"]
}

class HybridSearchEngine:
    def __init__(self, data_path: str = "data/properties.json"):
        self.data_path = data_path
        self.properties: List[Dict[str, Any]] = []
        self.corpus_tokens: List[List[str]] = []
        self.doc_freq: Dict[str, int] = {}
        self.avg_doc_len: float = 0.0
        self.k1: float = 1.5
        self.b: float = 0.75
        self.catalog_cities: Dict[str, str] = {}
        self.catalog_countries: Dict[str, str] = {}
        self.catalog_districts: Dict[str, str] = {}
        self.catalog_locations: Set[str] = set()
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
        self.catalog_cities = {}
        self.catalog_countries = {}
        self.catalog_districts = {}
        self.catalog_locations = set()

        for p in self.properties:
            doc_text = f"{p.get('title', '')} {p.get('project_name', '')} {p.get('brand_partner', '')} {p.get('developer', '')} {p.get('city', '')} {p.get('country', '')} {p.get('district', '')} {p.get('property_type', '')} {p.get('description', '')} {' '.join(p.get('amenities', []))}"
            tokens = self.tokenize(doc_text)
            self.corpus_tokens.append(tokens)
            total_len += len(tokens)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.doc_freq[t] = self.doc_freq.get(t, 0) + 1

            city = p.get("city")
            if city:
                city_clean = city.strip()
                for segment in re.split(r"[,/]", city_clean):
                    seg_clean = segment.strip()
                    seg_lower = seg_clean.lower()
                    if len(seg_lower) > 2 and seg_lower not in STOPWORDS:
                        if seg_lower not in self.catalog_cities or len(seg_clean) < len(self.catalog_cities[seg_lower]):
                            self.catalog_cities[seg_lower] = seg_clean
                        self.catalog_locations.add(seg_lower)

            country = p.get("country")
            if country:
                country_clean = country.strip()
                for segment in re.split(r"[,/]", country_clean):
                    seg_clean = segment.strip()
                    seg_lower = seg_clean.lower()
                    if len(seg_lower) > 2 and seg_lower not in STOPWORDS:
                        if seg_lower not in self.catalog_countries or len(seg_clean) < len(self.catalog_countries[seg_lower]):
                            self.catalog_countries[seg_lower] = seg_clean
                        self.catalog_locations.add(seg_lower)

            district = p.get("district")
            if district:
                dist_clean = district.strip()
                self.catalog_districts[dist_clean.lower()] = dist_clean
                self.catalog_locations.add(dist_clean.lower())
                for t in self.tokenize(dist_clean):
                    if t not in STOPWORDS and t not in GENERIC_DESCRIPTORS:
                        self.catalog_districts[t] = dist_clean
                        self.catalog_locations.add(t)

        common_aliases = {
            "uae": "United Arab Emirates",
            "ksa": "Saudi Arabia",
            "uk": "United Kingdom",
            "britain": "United Kingdom",
            "saudi": "Saudi Arabia",
            "emirates": "United Arab Emirates"
        }
        for alias, canon in common_aliases.items():
            if canon.lower() in self.catalog_countries:
                self.catalog_countries[alias] = canon
                self.catalog_locations.add(alias)

        self.avg_doc_len = (total_len / len(self.properties)) if self.properties else 1.0

    def parse_query_constraints(self, query: str, query_tokens: List[str]) -> Dict[str, Any]:
        lowered = query.lower()
        constraints = {}

        if "darglobal" in lowered or "dar global" in lowered:
            constraints["platform"] = "DarGlobal"
        elif "wasalt" in lowered:
            constraints["platform"] = "Wasalt"

        for token in query_tokens:
            if token in self.catalog_cities:
                constraints["city"] = self.catalog_cities[token]
                break

        for token in query_tokens:
            if token in self.catalog_countries:
                constraints["country"] = self.catalog_countries[token]
                break

        for key, targets in PROPERTY_TYPES_MAP.items():
            if re.search(r"\b" + re.escape(key) + r"\b", lowered):
                constraints["property_type_targets"] = targets
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

    def is_query_out_of_catalog(self, query: str, query_tokens: List[str], parsed: Dict[str, Any]) -> bool:
        lowered = query.lower()

        loc_targets = re.findall(r"\b(?:in|at|near|around|from)\s+([a-zA-Z\u0600-\u06FF]+)", lowered)
        for target in loc_targets:
            target_clean = target.strip()
            if target_clean in STOPWORDS or target_clean in GENERIC_DESCRIPTORS:
                continue
            if target_clean not in self.catalog_locations:
                has_any_supported = any(loc in query_tokens for loc in self.catalog_locations)
                if not has_any_supported:
                    return True

        facet_words = set()
        if parsed.get("city"):
            facet_words.add(parsed["city"].lower())
            for t in self.tokenize(parsed["city"]):
                facet_words.add(t)
        if parsed.get("country"):
            facet_words.add(parsed["country"].lower())
            for t in self.tokenize(parsed["country"]):
                facet_words.add(t)
        if parsed.get("platform"):
            facet_words.add(parsed["platform"].lower())

        content_tokens = [
            t for t in query_tokens 
            if not t.isdigit() and t not in GENERIC_DESCRIPTORS and t not in facet_words
        ]

        if content_tokens:
            has_any_presence = any(ct in self.doc_freq for ct in content_tokens)
            if not has_any_presence:
                return True

        return False

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
        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        parsed = self.parse_query_constraints(query, query_tokens)
        if explicit_filters:
            parsed.update({k: v for k, v in explicit_filters.items() if v is not None})

        if self.is_query_out_of_catalog(query, query_tokens, parsed):
            return []

        facet_words = set()
        if parsed.get("city"):
            facet_words.add(parsed["city"].lower())
            for t in self.tokenize(parsed["city"]):
                facet_words.add(t)
        if parsed.get("country"):
            facet_words.add(parsed["country"].lower())
            for t in self.tokenize(parsed["country"]):
                facet_words.add(t)
        if parsed.get("platform"):
            facet_words.add(parsed["platform"].lower())

        content_tokens = [
            t for t in query_tokens 
            if not t.isdigit() and t not in GENERIC_DESCRIPTORS and t not in facet_words
        ]

        candidates = []

        for idx, p in enumerate(self.properties):
            if parsed.get("platform"):
                if p.get("platform", "").lower() != parsed["platform"].lower():
                    continue

            if parsed.get("city"):
                if parsed["city"].lower() not in p.get("city", "").lower():
                    continue

            if parsed.get("country"):
                if parsed["country"].lower() not in p.get("country", "").lower():
                    continue

            if parsed.get("max_price"):
                if p.get("price_sar", 0.0) > (parsed["max_price"] * 1.05):
                    continue

            if parsed.get("bedrooms") is not None:
                p_beds = p.get("bedrooms")
                p_min = p.get("bedrooms_min")
                p_max = p.get("bedrooms_max")
                if p_min is not None and p_max is not None:
                    if not (p_min <= parsed["bedrooms"] <= p_max):
                        continue
                elif p_beds is not None:
                    if p_beds != parsed["bedrooms"]:
                        continue

            if parsed.get("property_type_targets"):
                doc_ptype = p.get("property_type", "").lower()
                doc_title = p.get("title", "").lower()
                matched_ptype = any(target in doc_ptype or target in doc_title for target in parsed["property_type_targets"])
                if not matched_ptype:
                    continue

            if parsed.get("listing_type"):
                if p.get("listing_type", "").lower() != parsed["listing_type"].lower():
                    continue

            doc_tokens_set = set(self.corpus_tokens[idx])
            if content_tokens and not (parsed.get("city") or parsed.get("country")):
                matched_count = sum(1 for ct in content_tokens if ct in doc_tokens_set)
                coverage = matched_count / len(content_tokens)
                if coverage < 0.5:
                    continue

            bm25 = self.score_bm25(query_tokens, idx)
            threshold = 0.5 if content_tokens else 1.0
            if bm25 >= threshold:
                candidates.append((bm25, p))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in candidates[:top_k]]

search_engine = HybridSearchEngine()
