import json
import logging
import os
from router.engine import RouterEngine
from router.providers.base import ProviderError

logger = logging.getLogger(__name__)

AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.3"))
AI_MODEL = os.getenv("AI_MODEL", "llama-3.3-70b")

_engine = None

def _get_engine() -> RouterEngine:
    global _engine
    if _engine is None:
        _engine = RouterEngine()
    return _engine

async def _call_ai(prompt: str, model: str = None) -> str:
    engine = _get_engine()
    model_id = model or AI_MODEL
    try:
        result = await engine.ask(model_id, prompt, temperature=AI_TEMPERATURE)
        return result
    except ProviderError as e:
        logger.warning("Primary model %s failed: %s. Trying fallback...", model_id, e)
        fallbacks = ["gemini-2.0-flash", "llama-3.3-70b", "llama-3.1-8b"]
        for fb in fallbacks:
            if fb == model_id:
                continue
            try:
                result = await engine.ask(fb, prompt, temperature=AI_TEMPERATURE)
                return result
            except ProviderError:
                continue
        raise RuntimeError(f"All AI providers failed for prompt: {e}")

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
        result = await _call_ai("cv_parse -- " + raw_text[:1000])
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
        result = await _call_ai("cover_letter -- " + job_title[:50])
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
        result = await _call_ai("personas -- " + (pi.get('currentTitle', '') or 'profile'))
        cleaned = _clean_json(result)
        data = json.loads(cleaned)
        return data.get("profiles", [])
    except Exception as e:
        return [{"error": str(e)}]
