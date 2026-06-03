import httpx
import json
import logging
import os
from database.config import ROUTEMCP_ENABLED

logger = logging.getLogger(__name__)

ROUTEMCP_URL = os.getenv("ROUTEMCP_URL", "http://localhost:8000")

async def _call_routemcp(action: str, prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
    if not ROUTEMCP_ENABLED:
        raise RuntimeError("RouteMCP is not enabled. Set ROUTEMCP_ENABLED=true")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{ROUTEMCP_URL}/api/chat", json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            })
            resp.raise_for_status()
            data = resp.json()
            return data.get("content", "")
    except httpx.TimeoutException as e:
        logger.error("RouteMCP timeout for action=%s: %s", action, e)
        raise
    except Exception as e:
        logger.error("RouteMCP call failed for action=%s: %s", action, e)
        raise

def _clean_json(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        else:
            text = text[3:]
        end_marker = text.rfind("```")
        if end_marker != -1:
            text = text[:end_marker]
    return text.strip()

async def parse_cv_with_ai(raw_text: str) -> dict:
    prompt = f"""Eres un experto en extracción de datos de CVs. Extrae información estructurada de este CV en español.

Texto del CV:
{raw_text[:25000]}

Responde ÚNICAMENTE con un JSON con esta estructura:
{{
  "personalInfo": {{"firstName": str, "lastName": str, "email": str, "phone": str, "city": str, "country": str, "currentTitle": str, "linkedin": str, "github": str, "summary": str}},
  "experience": [{{"title": str, "company": str, "location": str, "startDate": str, "endDate": str, "current": bool, "description": str}}],
  "education": [{{"degree": str, "school": str, "fieldOfStudy": str, "startDate": str, "endDate": str, "current": bool}}],
  "skills": [str],
  "certifications": [{{"name": str, "issuer": str, "date": str}}],
  "languages": [{{"language": str, "level": str}}]
}}
Usa null para campos sin datos, array vacío para listas sin datos."""
    try:
        result = await _call_routemcp("cv_parse", prompt)
        cleaned = _clean_json(result)
        return json.loads(cleaned)
    except Exception as e:
        return {"error": str(e)}

async def generate_cover_letter(profile: dict, job_title: str, company: str, job_description: str, tone: str = "professional") -> str:
    tones = {
        "professional": "formal y corporativo, apropiado para empresas establecidas",
        "casual": "amigable y cercano, apropiado para startups",
        "technical": "técnico y detallado, enfocado en habilidades y logros específicos",
    }
    tone_desc = tones.get(tone, tones["professional"])

    pi = profile.get("personalInfo", {})
    exp_text = "\n".join(
        f"- {e['title']} en {e['company']}: {e.get('description', '')[:200]}"
        for e in profile.get("experience", [])[:3]
    )
    skills_text = ", ".join(profile.get("skills", [])[:10])

    prompt = f"""Genera una carta de presentación {tone_desc} para:

Puesto: {job_title}
Empresa: {company}
Descripción del trabajo: {job_description}

Mi perfil:
- Nombre: {pi.get('firstName', pi.get('first_name', ''))} {pi.get('lastName', pi.get('last_name', ''))}
- Título: {pi.get('currentTitle', pi.get('current_title', ''))}
- Resumen: {pi.get('summary', '')}

Experiencia relevante:
{exp_text}

Habilidades: {skills_text}

Requisitos:
- 250-300 palabras
- Idioma: Español
- Destacar experiencia que coincida con la descripción del trabajo
- NO incluir dirección, fecha, ni firma
- Genera SOLO el cuerpo de la carta"""
    try:
        result = await _call_routemcp("cover_letter", prompt, model="llama-3.3-70b-versatile")
        return _clean_json(result)
    except Exception as e:
        return f"Error generando carta: {e}"

async def generate_personas(profile: dict) -> list:
    pi = profile.get("personalInfo", {})
    exp_text = "\n".join(
        f"- {e['title']} en {e['company']} ({e.get('startDate', '')} - {e.get('endDate', '')})"
        for e in profile.get("experience", [])
    )
    edu_text = "\n".join(
        f"- {e['degree']} en {e['school']}" for e in profile.get("education", [])
    )
    skills_text = ", ".join(profile.get("skills", []))

    prompt = f"""Analiza este CV y genera 3 perfiles profesionales DIFERENTES pero complementarios que maximicen oportunidades de empleo.

Datos del candidato:
Nombre: {pi.get('firstName', pi.get('first_name', ''))} {pi.get('lastName', pi.get('last_name', ''))}
Título: {pi.get('currentTitle', pi.get('current_title', ''))}
Ubicación: {pi.get('city', '')}, {pi.get('country', '')}
Resumen: {pi.get('summary', '')}

Experiencia:
{exp_text}

Educación:
{edu_text}

Habilidades: {skills_text}

Responde ÚNICAMENTE con JSON:
{{"profiles": [
  {{"title": str, "description": str, "keySkills": [str], "searchKeywords": [str], "targetRoles": [str]}}
]}}"""
    try:
        result = await _call_routemcp("personas", prompt)
        cleaned = _clean_json(result)
        data = json.loads(cleaned)
        return data.get("profiles", [])
    except Exception as e:
        return [{"error": str(e)}]
