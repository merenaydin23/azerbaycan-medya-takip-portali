import re
from config import KEYWORDS_STAGE_1, STAGE2_CONTEXT_TOPICS

# Short / ambiguous tokens that must match as whole words only
WEAK_KEYWORDS = {"tap", "tdt", "btc", "aliyev"}

# Strong keywords: direct Azerbaijan markers (substring OK only with word boundaries)
def _compile_kw(kw: str):
    # Use Unicode-aware word-ish boundaries: not letter/digit on either side
    return re.compile(rf"(?<![\wçğıöşüÇĞİÖŞÜ]){re.escape(kw)}(?![\wçğıöşüÇĞİÖŞÜ])", re.IGNORECASE)

STAGE1_PATTERNS = [(_compile_kw(kw), kw) for kw in KEYWORDS_STAGE_1]
STAGE2_CONTEXT_PATTERNS = [(_compile_kw(topic), topic) for topic in STAGE2_CONTEXT_TOPICS]

# Aspect keyword groups (word-boundary safe)
ASPECT_ARMENIA = ["ermenistan", "paşinyan", "zangezur", "zengezur", "laçın", "hankendi", "hocalı", "sınır komisyonu", "barış anlaşması", "üçlü bildiri"]
ASPECT_SECURITY = ["şuşa beyannamesi", "savunma", "askeri", "tatbikat", "ordu", "mayın temizleme", "güvenlik", "savunma bakanlığı", "zakir hasanov", "silahlı kuvvetler"]
ASPECT_ENERGY = ["tanap", "tap", "petkim", "socar", "boru hattı", "enerji", "şahdeniz", "şah deniz", "btc", "doğalgaz", "petrol", "gaz", "ticaret", "yatırım", "ekonomi"]
ASPECT_TURKIC = ["türk devletleri teşkilatı", "tdt", "türk konverse", "türk konseyi", "türksoy", "turkpa", "orta asya", "türk dünyası"]
ASPECT_DIPLOMACY = ["diplomasi", "siyaset", "büyükelçi", "büyükelçilik", "başkonsolosluk", "konsolos", "ziyaret", "görüşme", "zirve", "dışişleri", "ceyhun bayramov", "reşad memmedov", "milli meclis"]

ASPECT_ARMENIA_PATTERNS = [_compile_kw(k) for k in ASPECT_ARMENIA]
ASPECT_SECURITY_PATTERNS = [_compile_kw(k) for k in ASPECT_SECURITY]
ASPECT_ENERGY_PATTERNS = [_compile_kw(k) for k in ASPECT_ENERGY]
ASPECT_TURKIC_PATTERNS = [_compile_kw(k) for k in ASPECT_TURKIC]
ASPECT_DIPLOMACY_PATTERNS = [_compile_kw(k) for k in ASPECT_DIPLOMACY]

# Place-name false friends & Turkish homonym phrases (Turkish localities / common nouns ≠ Azerbaijan)
FALSE_FRIEND_PATTERNS = [
    _compile_kw("karabağlar"),  # İzmir Karabağlar ilçesi
    _compile_kw("karabağ mahallesi"),
    _compile_kw("karabağ caddesi"),
    _compile_kw("karabağ sokak"),
    _compile_kw("karabağ köyü"),

    # Turkish noun case homonym phrases ("genç-e" / young person ≠ Gence city)
    re.compile(r"\b(?:yerdeki|talihsiz|yaralı|genç|kavga|şiddet|video|haber)\s+gence\b", re.IGNORECASE),
    re.compile(r"\bgence\s+(?:saldırdı|tekmeler|bağırdı|vurdu|dehşet|dayak|kavga)\b", re.IGNORECASE),

    # Turkish noun case homonym phrases ("bar-da" / in the bar ≠ Barda city)
    re.compile(r"\bbarda\s+(?:kavga|dehşet|olay|cinayet|silahlı|eğlenen|tartışma)\b", re.IGNORECASE),
]


def check_stage1_relevance(title: str, summary: str) -> dict:
    """
    Stage 1: Fast keyword matching with word boundaries (no substring false positives).
    """
    text = f"{title or ''} {summary or ''}"

    # Filter out Turkish locality false friends (e.g. İzmir Karabağlar)
    text_for_match = text
    for fp in FALSE_FRIEND_PATTERNS:
        if fp.search(text_for_match):
            text_for_match = fp.sub(" ", text_for_match)

    matched_keywords = []
    for pattern, kw in STAGE1_PATTERNS:
        if pattern.search(text_for_match):
            matched_keywords.append(kw)

    if matched_keywords:
        # If ONLY weak keywords matched, send to Stage 2 for verification
        strong = [k for k in matched_keywords if k.lower() not in WEAK_KEYWORDS]
        if not strong:
            return {
                "is_relevant": False,
                "stage": None,
                "is_candidate_for_stage2": True,
                "matched_keywords": matched_keywords[:5],
                "explanation": f"Zayıf anahtar kelime (LLM doğrulaması gerekli): {', '.join(matched_keywords[:3])}"
            }

        # Fine-grained Aspect Detection
        aspect = "Diplomasi & Siyaset"
        if any(p.search(text_for_match) for p in ASPECT_ARMENIA_PATTERNS) or any(k in ("ermenistan-azerbaycan", "azerbaycan-ermenistan", "paşinyan", "karabağ", "dağlık karabağ", "zangezur", "zengezur") for k in matched_keywords):
            aspect = "Ermenistan Hattı"
        elif any(p.search(text_for_match) for p in ASPECT_SECURITY_PATTERNS):
            aspect = "Güvenlik / Savunma"
        elif any(p.search(text_for_match) for p in ASPECT_ENERGY_PATTERNS):
            aspect = "Enerji / Ekonomi"
        elif any(p.search(text_for_match) for p in ASPECT_TURKIC_PATTERNS):
            aspect = "Türk Devletleri/Bölgesel"
        elif any(p.search(text_for_match) for p in ASPECT_DIPLOMACY_PATTERNS):
            aspect = "Diplomasi & Siyaset"

        return {
            "is_relevant": True,
            "stage": "Stage 1 (Anahtar Kelime)",
            "aspect": aspect,
            "matched_keywords": matched_keywords[:5],
            "explanation": f"Metinde doğrudan anahtar kelime eşleşmesi bulundu: {', '.join(matched_keywords[:3])}"
        }

    is_candidate_for_stage2 = any(p.search(text) for p, _ in STAGE2_CONTEXT_PATTERNS)

    return {
        "is_relevant": False,
        "stage": None,
        "is_candidate_for_stage2": is_candidate_for_stage2,
        "matched_keywords": [],
        "explanation": ""
    }
