import re
from typing import Tuple, Optional

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above)\s+instructions?",
    r"system\s+prompt",
    r"reveal\s+(your|the)\s+(system|initial)\s+(prompt|instructions?)",
    r"you\s+are\s+now\s+(DAN|unrestricted|in\s+developer\s+mode)",
    r"disregard\s+(all\s+)?prior\s+guidelines?",
    r"bypass\s+(all\s+)?content\s+filters?",
    r"sudo\s+mode",
    r"jailbreak"
]

DOMAIN_KEYWORDS = [
    "property", "properties", "real estate", "house", "villa", "villas", "apartment", "apartments",
    "flat", "flats", "penthouse", "penthouses", "mansion", "mansions", "land", "plot", "rent", "buy",
    "sale", "darglobal", "dar global", "wasalt", "dar al arkan", "riyadh", "jeddah", "dammam", "khobar",
    "makkah", "medina", "dubai", "oman", "qatar", "spain", "marbella", "london", "costa del sol",
    "dg1", "pagani", "davinci", "missoni", "urban oasis", "aida", "tierra viva", "lamborghini",
    "neptune", "mouawad", "trump", "elies saab", "astera", "aston martin", "sedra", "al malqa",
    "price", "budget", "bedroom", "bedrooms", "bhk", "sqm", "sar", "aed", "omr", "eur", "invest",
    "investment", "roi", "yield", "down payment", "handover", "off-plan", "ready", "amenities",
    "hi", "hello", "hey", "who are you", "help", "good morning", "good evening", "welcome", "marhaba",
    "salam", "السلام", "عقار", "فيلا", "شقة", "شقق", "فلل", "الرياض", "جدة", "دار الأركان", "وصلت", "دار غلوبال"
]

class GuardrailsEngine:
    def __init__(self):
        self.injection_regex = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

    def check_injection(self, text: str) -> bool:
        for pattern in self.injection_regex:
            if pattern.search(text):
                return True
        return False

    def is_in_domain(self, text: str) -> bool:
        lowered = text.lower().strip()
        if len(lowered) < 4:
            return True
        for kw in DOMAIN_KEYWORDS:
            if kw in lowered:
                return True
        return False

    def sanitize_input(self, text: str) -> str:
        cc_pattern = r"\b(?:\d{4}[ -]?){3}\d{4}\b"
        sanitized = re.sub(cc_pattern, "[REDACTED_CARD]", text)
        return sanitized

    def evaluate_input(self, user_text: str) -> Tuple[bool, Optional[str], str]:
        if self.check_injection(user_text):
            return False, "Security Notice: Prompt injection or system instruction override attempt detected. I am exclusively configured to act as a grounded Real Estate Advisor for DarGlobal and Wasalt.", "injection_blocked"
        
        if not self.is_in_domain(user_text):
            return False, "I specialize exclusively in luxury real estate investments with DarGlobal and residential/commercial properties across Saudi Arabia with Wasalt. How can I assist your property search, budget, or investment goals today?", "off_domain"
        
        return True, None, "passed"

    def verify_grounding(self, response_text: str, retrieved_titles: list) -> str:
        if not retrieved_titles:
            return response_text
        return response_text

guardrails_engine = GuardrailsEngine()
