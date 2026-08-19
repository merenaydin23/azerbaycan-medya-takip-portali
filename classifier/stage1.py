import re
from config import KEYWORDS_STAGE_1, STAGE2_CONTEXT_TOPICS

# Compile regex patterns for performance
STAGE1_PATTERNS = [re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE) for kw in KEYWORDS_STAGE_1]
STAGE2_CONTEXT_PATTERNS = [re.compile(r'\b' + re.escape(topic) + r'\b', re.IGNORECASE) for topic in STAGE2_CONTEXT_TOPICS]

def check_stage1_relevance(title: str, summary: str) -> dict:
    """
    Stage 1: Fast, local keyword matching against title and summary.
    Returns dict with relevance status and matched keywords.
    """
    text = f"{title or ''} {summary or ''}".lower()
    
    matched_keywords = []
    for kw in KEYWORDS_STAGE_1:
        if kw in text:
            matched_keywords.append(kw)

    if matched_keywords:
        # Determine likely aspect based on keywords
        aspect = "Siyasi"
        if any(k in text for k in ["tanap", "tap", "petkim", "socar", "boru hattı", "enerji", "şahdeniz", "şah deniz", "btc"]):
            aspect = "Enerji / Ekonomi"
        elif any(k in text for k in ["şuşa beyannamesi", "savunma", "askeri", "tatbikat", "ordu"]):
            aspect = "Güvenlik / Savunma"
        elif any(k in text for k in ["türk devletleri teşkilatı", "tdt", "kültür", "ziyaret", "büyükelçi"]):
            aspect = "Diplomatik / Kültürel"

        return {
            "is_relevant": True,
            "stage": "Stage 1 (Anahtar Kelime)",
            "aspect": aspect,
            "matched_keywords": matched_keywords[:5],
            "explanation": f"Metinde doğrudan anahtar kelime eşleşmesi bulundu: {', '.join(matched_keywords[:3])}"
        }

    # Check if this article belongs to candidate topics for Stage 2
    is_candidate_for_stage2 = any(topic in text for topic in STAGE2_CONTEXT_TOPICS)

    return {
        "is_relevant": False,
        "stage": None,
        "is_candidate_for_stage2": is_candidate_for_stage2,
        "matched_keywords": [],
        "explanation": ""
    }
