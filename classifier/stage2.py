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

def call_llm(messages: list, temperature: float = 0.2, max_tokens: int = 800) -> str:
    """
    Calls the custom Qwen endpoint via OpenAI compatible chat/completions API.
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
        response = requests.post(url, headers=headers, json=payload, timeout=90, verify=False)
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

def generate_qwen_summary(title: str, text: str) -> str:
    """
    Generates a concise 2-sentence summary of the news article using Qwen LLM.
    """
    prompt = f"""Haber Başlığı: {title}
Haber Metni: {text}

Görev: Bu haber için en fazla 2 cümlelik, net, tarafsız ve profesyonel bir Türkçe özet yaz.
Doğrudan özeti <summary>...</summary> etiketleri içerisine yaz. Başka hiçbir şey yazma."""

    messages = [
        {"role": "system", "content": "Sen hızlı haber özetleyen bir asistansın. Yalnızca <summary> ve </summary> etiketleri arasına en fazla 2 cümlelik Türkçe özet yazarsın."},
        {"role": "user", "content": prompt}
    ]
    response_text = call_llm(messages, temperature=0.2, max_tokens=1500)
    if response_text:
        # Try to extract content between <summary> tags
        match = re.search(r'<summary>(.*?)</summary>', response_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
            
        # Fallback if tags not found
        response_text = re.sub(r'(?i)<thinking>.*?</thinking>', '', response_text, flags=re.DOTALL)
        response_text = re.sub(r'(?i)^thinking\s*process:.*?\n', '', response_text)
        response_text = re.sub(r'^(Özet:|Özetçe:|Xülasə:)\s*', '', response_text.strip(), flags=re.IGNORECASE)
        return response_text.strip()
    return ""
