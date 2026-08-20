import json
import logging
import re
import requests
import urllib3
from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

urllib3.disable_warnings()
logger = logging.getLogger("Classifier.Stage2")

def extract_json_object(text: str) -> str:
    """Extracts valid JSON object {...} from text reliably."""
    if not text:
        return ""
    
    # 1. Search for json markdown blocks ```json ... ```
    blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if blocks:
        for b in reversed(blocks):
            try:
                json.loads(b)
                return b
            except:
                pass

    # 2. Search for all top-level {...} matches from end to start
    matches = list(re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL))
    if matches:
        for m in reversed(matches):
            try:
                cand = m.group(0)
                json.loads(cand)
                return cand
            except:
                pass

    # 3. Fallback to outermost { and }
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return ""

def call_llm(messages: list, temperature: float = 0.2, max_tokens: int = 600) -> str:
    """
    Calls the LLM endpoint via OpenAI compatible chat/completions API with fast timeout.
    """
    if not LLM_API_KEY:
        logger.warning("LLM_API_KEY is not set. Skipping LLM request.")
        return ""

    url = f"{LLM_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}"
    }
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=6, verify=False)
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            logger.error(f"LLM API returned status {response.status_code}: {response.text}")
            return ""
    except Exception as e:
        logger.error(f"Error connecting to LLM API ({url}): {e}")
        return ""

from .azerbaijan_relevance_prompt import AZERBAIJAN_RELEVANCE_SYSTEM_PROMPT, build_relevance_user_prompt

def check_stage2_llm_relevance(title: str, summary: str, source_name: str = "Bilinmeyen", category: str = "Genel") -> dict:
    """
    Evaluates direct or indirect relevance to Azerbaijan using Qwen LLM and returns structured classification.
    """
    user_prompt = build_relevance_user_prompt(
        kaynak_adi=source_name or "Bilinmeyen",
        kategori=category or "Genel",
        baslik=title or "",
        ozet=summary or ""
    )

    messages = [
        {"role": "system", "content": AZERBAIJAN_RELEVANCE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    response_text = call_llm(messages, temperature=0.2, max_tokens=4000)
    if not response_text:
        return {
            "ilgili_mi": False,
            "ilgi_kategorisi": "İlgisiz",
            "guven_skoru": 0.0,
            "gerekce": "LLM yanıt veremedi veya API anahtarı girilmedi.",
            "is_relevant": False,
            "stage": None,
            "aspect": "",
            "explanation": "LLM yanıt veremedi veya API anahtarı girilmedi."
        }

    try:
        clean_json_str = extract_json_object(response_text)
        if not clean_json_str:
            raise ValueError("No JSON object found in response.")

        result = json.loads(clean_json_str)
        ilgili_mi = bool(result.get("ilgili_mi", False))
        ilgi_kategorisi = str(result.get("ilgi_kategorisi", "İlgisiz")).strip()
        guven_skoru = float(result.get("guven_skoru", 1.0 if ilgili_mi else 0.0))
        gerekce = str(result.get("gerekce", "")).strip()

        if not ilgili_mi:
            ilgi_kategorisi = "İlgisiz"

        return {
            "ilgili_mi": ilgili_mi,
            "ilgi_kategorisi": ilgi_kategorisi,
            "guven_skoru": guven_skoru,
            "gerekce": gerekce,
            "is_relevant": ilgili_mi,
            "stage": "Stage 2 (LLM)",
            "aspect": ilgi_kategorisi if ilgili_mi else "",
            "explanation": gerekce if ilgili_mi else ""
        }
    except Exception as e:
        logger.error(f"Error parsing LLM response '{response_text}': {e}")
        return {
            "ilgili_mi": False,
            "ilgi_kategorisi": "İlgisiz",
            "guven_skoru": 0.0,
            "gerekce": "",
            "is_relevant": False,
            "stage": None,
            "aspect": "",
            "explanation": ""
        }


def clean_llm_summary_output(response_text: str) -> str:
    """Cleans LLM response text, stripping reasoning steps and CoT monologues."""
    if not response_text:
        return ""

    # 1. Extract content inside <summary>...</summary> tags if present
    match = re.search(r"<summary>(.*?)</summary>", response_text, re.DOTALL | re.IGNORECASE)
    if match:
        extracted = match.group(1).strip()
        if extracted and not ("Analyze the Request" in extracted or "Internal Monologue" in extracted):
            return extracted

    # 2. Remove thinking tags <thinking>...</thinking> or <think>...</think>
    text = re.sub(r"(?i)<think(?:ing)?>.*?</think(?:ing)?>", "", response_text, flags=re.DOTALL)

    # 3. If response contains CoT monologue ("Analyze the Request", "Drafting", "Attempt"), extract final attempt or filter lines
    if "Analyze the Request" in text or "Drafting" in text or "Internal Monologue" in text or "Attempt" in text:
        attempts = re.findall(r'Attempt\s*\d+:\*?\s*([^\n\r]+)', text)
        if attempts:
            text = attempts[-1].strip()
        else:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            filtered = [
                l for l in lines 
                if not re.match(r'^(\d+\.|\*)\s*\*\*(Analyze|Drafting|Role|Task|Constraint|Input|Person|Action|Event|Source)', l, re.IGNORECASE)
                and not l.startswith("```")
                and not l.startswith("Attempt")
            ]
            text = " ".join(filtered)

    # 4. Remove prefix labels like "Özet:", "Özetçe:", "Xülasə:", "Summary:"
    text = re.sub(r"^(Özet:|Özetçe:|Xülasə:|Summary:)\s*", "", text.strip(), flags=re.IGNORECASE)

    # 5. Clean trailing/leading Markdown and quotes
    text = text.strip('"` ')
    return text


def generate_az_agenda_brief(title: str, text: str, ilgi_kategorisi: str = "") -> str:
    """
    Azerbaycan Gündemi haberleri için genel, anlaşılır 2-3 cümlelik içerik özeti.
    """
    kategori = ilgi_kategorisi or "Azerbaycan Gündemi"
    prompt = f"""Haber Başlığı: {title}
Haber Metni: {text or title}
İlgi Açısı: {kategori}

GÖREV: Bu Azerbaycan gündemi haberinin içeriğini genel ve net şekilde 2 veya 3 Türkçe cümle ile özetle.
ÖNEMLİ KURAL: Kesinlikle analiz adımları, reasoning, 'Analyze the Request', madde işaretleri veya ingilizce açıklamalar YAZMA!
Yalnızca net Türkçe özeti <summary> ve </summary> etiketleri arasına koy."""

    messages = [
        {
            "role": "system",
            "content": (
                "Sen Azerbaycan gündemi için doğrudan kurumsal brifing özeti üreten bir yapay zekasın. "
                "HİÇBİR düşünce adımı veya ingilizce analiz metni yazmadan YALNIZCA <summary>...</summary> içine 2-3 Türkçe özet cümlesi yazarsın."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    response_text = call_llm(messages, temperature=0.1, max_tokens=600)
    return clean_llm_summary_output(response_text)
