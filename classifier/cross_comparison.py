import json
import logging
from collections import defaultdict
from .stage2 import call_llm
from db import update_inconsistency

logger = logging.getLogger("Classifier.CrossComparison")

def extract_topic_keywords(title: str, summary: str) -> set:
    text = f"{title} {summary}".lower()
    words = set()
    for token in text.split():
        token = token.strip(".,;:!?\"'()[]{}«»")
        if len(token) > 4:
            words.add(token)
    return words

def group_articles_by_similarity(articles: list) -> list:
    """
    Groups articles into clusters based on shared keywords and topic words.
    Returns list of article lists (groups with >= 2 items).
    """
    if len(articles) < 2:
        return []

    groups = []
    visited = set()

    for i, a1 in enumerate(articles):
        if i in visited:
            continue
        current_group = [a1]
        visited.add(i)
        tokens1 = extract_topic_keywords(a1.get("title", ""), a1.get("summary", ""))

        for j in range(i + 1, len(articles)):
            if j in visited:
                continue
            a2 = articles[j]
            tokens2 = extract_topic_keywords(a2.get("title", ""), a2.get("summary", ""))
            
            # If they share >= 3 significant words or both mention specific key terms
            intersection = tokens1.intersection(tokens2)
            if len(intersection) >= 3 or (len(intersection) >= 2 and any(k in intersection for k in ["aliyev", "zengezur", "karabağ", "ermenistan", "paşinyan", "şuşa", "tanap"])):
                current_group.append(a2)
                visited.add(j)

        if len(current_group) > 1:
            groups.append(current_group)

    return groups

def analyze_group_inconsistencies(group: list, group_index: int):
    """
    Sends a group of articles from different sources to Qwen LLM to check for discrepancies.
    """
    # Check if there are at least 2 distinct sources
    sources = set(a.get("source_name") for a in group)
    if len(sources) < 2:
        return

    articles_text = ""
    for idx, art in enumerate(group):
        articles_text += f"\n[Haber ID: {art['id']}] Kaynak: {art.get('source_name')} ({art.get('category')})\nBaşlık: {art.get('title')}\nÖzet: {art.get('summary')}\n"

    prompt = f"""Sen Azerbaycan Büyükelçiliği için çapraz kaynak karşılaştırması yapan kıdemli bir medya analistisin.
Aşağıda aynı konu hakkında Türkiye basınında farklı kaynaklarda (Resmi, İktidar Yanlısı, Muhalif) yayınlanan haberler listelenmiştir:

{articles_text}

GÖREV:
Bu haberleri çapraz olarak karşılaştır. Kaynaklar arasında dikkat çeken çelişkiler, farklı sayılar/rakamlar, çelişkili resmi/gayriresmi açıklamalar veya bir kaynağın verdiği önemli bir detayı diğerinin tamamen zıt sunması gibi bir tutarsızlık var mı?

ÖNEMLİ KURALLAR:
1. Kesin doğru/yanlış yargısında bulunma. Sadece kaynaklar arasındaki çelişkiyi veya sayı/ifade farkını özetle.
2. Eğer haberler birbirini doğruluyor ve aynı ana olayı anlatıyorsa "has_inconsistency": false döndür.
3. Yalnızca belirgin ve anlamlı bir fark/çelişki varsa "has_inconsistency": true döndür.

Yanıtını SADECE aşağıdaki JSON formatında ver:
{{
  "has_inconsistency": true veya false,
  "note": "Kaynaklar arasındaki farkı ve tutarsızlığı açıklayan 1-2 cümlelik özet not (büyükelçi için)",
  "inconsistent_article_ids": [ilgili haber id numaraları]
}}"""

    messages = [
        {"role": "system", "content": "Sen Azerbaycan Büyükelçiliği için medya tutarsızlık analizi yapan bir sistem modülüsün. Yalnızca geçerli JSON formatında yanıt ver."},
        {"role": "user", "content": prompt}
    ]

    response_text = call_llm(messages)
    if not response_text:
        return

    try:
        from .stage2 import extract_json_object
        clean_json_str = extract_json_object(response_text)
        if not clean_json_str:
            raise ValueError("No JSON object found in response.")

        data = json.loads(clean_json_str)
        has_inconsistency = bool(data.get("has_inconsistency", False))
        note = str(data.get("note", ""))
        inconsistent_ids = data.get("inconsistent_article_ids", [a["id"] for a in group])

        group_id_str = f"grp_{group_index}_{group[0]['id']}"

        for art in group:
            art_id = art["id"]
            if has_inconsistency and (art_id in inconsistent_ids or not inconsistent_ids):
                update_inconsistency(art_id, status=1, note=note, group_id=group_id_str)
            else:
                update_inconsistency(art_id, status=0, note="", group_id=group_id_str)

    except Exception as e:
        logger.error(f"Error in cross comparison analysis: {e}")

def run_cross_comparison_for_articles(articles: list):
    """
    Entry point for running cross comparison across a list of daily articles.
    """
    logger.info(f"Running cross comparison on {len(articles)} articles...")
    groups = group_articles_by_similarity(articles)
    logger.info(f"Formed {len(groups)} topic groups for comparison.")

    for idx, group in enumerate(groups):
        analyze_group_inconsistencies(group, idx + 1)
