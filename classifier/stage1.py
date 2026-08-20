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
ASPECT_ENERGY = ["tanap", "tap", "petkim", "socar", "boru hattı", "enerji", "şahdeniz", "şah deniz", "btc", "doğalgaz"]
ASPECT_SECURITY = ["şuşa beyannamesi", "savunma", "askeri", "tatbikat", "ordu"]
ASPECT_DIPLOMACY = ["türk devletleri teşkilatı", "tdt", "kültür", "ziyaret", "büyükelçi"]

ASPECT_ENERGY_PATTERNS = [_compile_kw(k) for k in ASPECT_ENERGY]
ASPECT_SECURITY_PATTERNS = [_compile_kw(k) for k in ASPECT_SECURITY]
ASPECT_DIPLOMACY_PATTERNS = [_compile_kw(k) for k in ASPECT_DIPLOMACY]

# Place-name false friends (Turkish localities ≠ Azerbaijan)
FALSE_FRIEND_PATTERNS = [
    _compile_kw("karabağlar"),  # İzmir ilçesi — Dağlık Karabağ değil
]


def check_stage1_relevance(title: str, summary: str) -> dict:
    """
    Stage 1: Fast keyword matching with word boundaries (no substring false positives).
    """
    text = f"{title or ''} {summary or ''}"
    text_lower = text.lower()

    # İzmir Karabağlar etc. must not trigger Karabağ
    for fp in FALSE_FRIEND_PATTERNS:
        if fp.search(text):
            # Strip the false-friend span so "karabağ" inside won't match via other means
            text_for_match = fp.sub(" ", text)
            break
    else:
        text_for_match = text

    matched_keywords = []
    for pattern, kw in STAGE1_PATTERNS:
        if pattern.search(text_for_match):
            matched_keywords.append(kw)

    if matched_keywords:
        # If ONLY weak keywords matched, do not auto-accept — send to Stage 2
        strong = [k for k in matched_keywords if k.lower() not in WEAK_KEYWORDS]
        if not strong:
            return {
                "is_relevant": False,
                "stage": None,
                "is_candidate_for_stage2": True,
                "matched_keywords": matched_keywords[:5],
                "explanation": f"Zayıf anahtar kelime (LLM doğrulaması gerekli): {', '.join(matched_keywords[:3])}"
            }

        aspect = "Diplomasi & Siyaset"
        if any(p.search(text_for_match) for p in ASPECT_ENERGY_PATTERNS):
            aspect = "Enerji / Ekonomi"
        elif any(p.search(text_for_match) for p in ASPECT_SECURITY_PATTERNS):
            aspect = "Güvenlik / Savunma"
        elif any(p.search(text_for_match) for p in ASPECT_DIPLOMACY_PATTERNS):
            aspect = "Türk Devletleri/Bölgesel"
        elif any(k in ("ermenistan-azerbaycan", "azerbaycan-ermenistan", "paşinyan", "karabağ", "dağlık karabağ", "zangezur", "zengezur") for k in matched_keywords):
            aspect = "Ermenistan Hattı"

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
