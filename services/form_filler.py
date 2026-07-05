import os
import re
import json
import logging
from enum import Enum


logger = logging.getLogger(__name__)


class QuestionType(Enum):
    TEXTAREA = "textarea"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    TEXT = "text"
    SELECT = "select"
    FILE = "file"
    HIDDEN = "hidden"
    EMAIL = "email"
    TEL = "tel"
    NUMBER = "number"
    DATE = "date"
    PASSWORD = "password"



class FormQuestion:
    def __init__(self, qtype: QuestionType, label: str, name: str,
                 required: bool = False, options: list = None,
                 placeholder: str = "", tag: str = "input"):
        self.type = qtype
        self.label = label
        self.name = name
        self.required = required
        self.options = options or []
        self.placeholder = placeholder
        self.tag = tag

    def __repr__(self):
        return f"FormQuestion({self.type.value}, '{self.label[:30]}', name='{self.name}')"


def _infer_type(tag: str, html_type: str) -> QuestionType:
    type_map = {
        "textarea": QuestionType.TEXTAREA,
        "radio": QuestionType.RADIO,
        "checkbox": QuestionType.CHECKBOX,
        "file": QuestionType.FILE,
        "hidden": QuestionType.HIDDEN,
        "email": QuestionType.EMAIL,
        "tel": QuestionType.TEL,
        "number": QuestionType.NUMBER,
        "date": QuestionType.DATE,
        "password": QuestionType.PASSWORD,
        "select": QuestionType.SELECT,
        "submit": QuestionType.HIDDEN,
    }
    if tag == "select":
        return QuestionType.SELECT
    if tag == "textarea":
        return QuestionType.TEXTAREA
    return type_map.get(html_type, QuestionType.TEXT)


def _normalize_label(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[¿¡]', '', text)
    text = re.sub(r'\?+$', '', text)
    return text.strip()


def parse_forms_json(forms_json: str) -> list[FormQuestion]:
    try:
        data = json.loads(forms_json)
        if isinstance(data, str):
            data = json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return _parse_forms_text(forms_json)

    questions = []
    if isinstance(data, dict):
        data = [data]
    
    for form in data if isinstance(data, list) else [data]:
        fields = form.get("fields", [])
        if isinstance(fields, str):
            try:
                fields = json.loads(fields)
            except json.JSONDecodeError:
                continue
        for field in fields:
            if isinstance(field, str):
                continue
            if not isinstance(field, dict):
                continue
            tag = field.get("tag", "input")
            html_type = field.get("type", "text")
            name = field.get("name", "")
            label = field.get("label", "")
            placeholder = field.get("placeholder", "")
            required = field.get("required", False)
            qtype = _infer_type(tag, html_type)
            if qtype == QuestionType.HIDDEN:
                continue
            found = _normalize_label(label or placeholder or name)
            opts = field.get("options", [])
            if isinstance(opts, str):
                try:
                    opts = json.loads(opts)
                except json.JSONDecodeError:
                    opts = []
            questions.append(FormQuestion(
                qtype=qtype,
                label=found,
                name=name,
                required=required,
                options=opts,
                placeholder=placeholder,
                tag=tag,
            ))
    
    return questions


def _parse_forms_text(text: str) -> list[FormQuestion]:
    questions = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        m = re.match(r'\s*\[(\w+)\]\s+(\S+)\s+\((\w+)\)(\s+\*)?', line)
        if m:
            tag, name, html_type = m.group(1), m.group(2), m.group(3)
            required = bool(m.group(4))
            qtype = _infer_type(tag, html_type)
            if qtype != QuestionType.HIDDEN:
                questions.append(FormQuestion(
                    qtype=qtype, label="", name=name,
                    required=required, tag=tag
                ))
        
        label_m = re.match(r'\s*Label:\s*(.+)', line)
        if label_m and questions:
            lbl = _normalize_label(label_m.group(1))
            questions[-1].label = lbl
    
    return questions

def _build_strategies(profile: dict):
    pi = profile.get("personalInfo", {})
    email = pi.get("email", "")
    phone = pi.get("phone", "")
    city = pi.get("city", "")
    skills = ", ".join(profile.get("skills", [])[:10])
    salary = profile.get("personalInfo", {}).get("salary_expectation", "")

    edu_lines = []
    for e in profile.get("education", []):
        status = "en curso" if e.get("current") else "completado"
        edu_lines.append(f"- {e['degree']} en {e['school']} ({status})")
    edu_text = "\n".join(edu_lines)

    exp_lines = []
    for e in profile.get("experience", [])[:3]:
        desc = (e.get("description") or "")[:200]
        exp_lines.append(f"- {e['title']} en {e['company']}: {desc}")
    exp_text = "\n".join(exp_lines)

    return [
        (r'(carrera|estudiando|semestre|año|estudios|formación académica|casa de estudios|universidad)',
         edu_text or "Formación según perfil."),
        (r'(horas|disponibilidad|práctica|full time|comenzar|inicio|jornada)',
         "Disponibilidad según lo requerido."),
        (r'(teléfono|correo|contacto|número|email)',
         f"{'Teléfono: ' + phone if phone else ''}{' | ' if phone and email else ''}{'Correo: ' + email if email else 'Datos de contacto en el perfil.'}"),
        (r'(experiencia|trayectoria|años)',
         exp_text or "Experiencia detallada en el perfil."),
        (r'(motivación|interés|por qué)',
         "Me interesa esta oportunidad para aplicar mis conocimientos y seguir creciendo profesionalmente."),
        (r'(comuna|residencia|vives|vive|domicilio|lugar)',
         f"{'Santiago, ' if city else ''}{city}".strip() or "Según perfil."),
        (r'(portfolio|github|linkedin|enlace)',
         f"{'GitHub: ' + pi.get('github', '') if pi.get('github') else ''}{' | ' if pi.get('github') and pi.get('linkedin') else ''}{'LinkedIn: ' + pi.get('linkedin', '') if pi.get('linkedin') else 'Datos en el perfil.'}"),
        (r'(conocimiento|tecnología|stack|técnico)',
         skills or "Según perfil profesional."),
        (r'(sueldo|salario|renta|pretensión)',
         salary if salary else os.environ.get("DEFAULT_SALARY", "")),
    ]


def generate_answer(question: FormQuestion, profile: dict) -> str:
    pi = profile.get("personalInfo", {})
    if question.type == QuestionType.EMAIL:
        return pi.get("email", "")
    if question.type == QuestionType.TEL:
        return pi.get("phone", "")

    label_lower = question.label.lower()
    patterns = _build_strategies(profile)
    for pattern, answer in patterns:
        if re.search(pattern, label_lower):
            return answer
    pi = profile.get("personalInfo", {})
    skills = ", ".join(profile.get("skills", [])[:8])
    return f"Sí, cuento con la experiencia y formación requerida. {pi.get('currentTitle', '')} con conocimientos en {skills}."


def generate_radio_answer(question: FormQuestion, profile: dict) -> str:
    label_lower = question.label.lower()
    
    negative_patterns = [
        r'^(no\s|no )',
        r'(discapacidad|enfermedad|problema)',
        r'(newsletter|notification|notificación|boletín|suscripción|ofertas|publicidad)',
    ]
    
    for pattern in negative_patterns:
        if re.search(pattern, label_lower):
            return "No"
    
    positive_patterns = [
        r'(disponibilidad|puedes|puede|cuentas|cuenta|tienes|tiene|conocimiento|experiencia)',
        r'(power bi|excel|base de datos|sql|python|programación|análisis)',
        r'(práctica profesional|full time|tiempo completo|presencial|remoto)',
        r'(seguro escolar|seguro)',
    ]
    
    for pattern in positive_patterns:
        if re.search(pattern, label_lower):
            return "Sí"

    return "Sí"


def _match_city(valid_opts, profile):
    city = profile.get("personalInfo", {}).get("city", "Santiago").lower()
    for opt in valid_opts:
        if city in opt.lower() or opt.lower() in city:
            return opt
    return None

def _match_country(valid_opts, profile):
    for opt in valid_opts:
        if "chile" in opt.lower():
            return opt
    return None

def _match_education(valid_opts, profile):
    for opt in valid_opts:
        if any(g in opt.lower() for g in ["universitario", "técnico", "superior", "educación superior", "pregrado"]):
            return opt
    return None

def _match_year(valid_opts, profile):
    for e in profile.get("education", []):
        year = str(e.get("year", "") or e.get("endYear", ""))
        if year:
            for opt in valid_opts:
                if year in opt:
                    return opt
    numeric_opts = [o for o in valid_opts if re.search(r'\d{4}', o)]
    return numeric_opts[0] if numeric_opts else None

def _match_degree(valid_opts, profile):
    for e in profile.get("education", []):
        degree = e.get("degree", "").lower()
        if degree:
            for opt in valid_opts:
                if degree in opt.lower() or opt.lower() in degree:
                    return opt
    return None

def _match_gender(valid_opts, profile):
    for opt in valid_opts:
        if any(g in opt.lower() for g in ["masculino", "hombre", "varón"]):
            return opt
    return None

_SELECT_RULES = [
    (["comuna", "ciudad", "región", "region"], _match_city),
    (["país", "pais"], _match_country),
    (["escolaridad", "educación", "educacion", "estudios", "nivel académico", "nivel academico"], _match_education),
    (["año", "year", "semestre", "nivel"], _match_year),
    (["carrera", "título", "titulo", "grado"], _match_degree),
    (["género", "genero", "sexo"], _match_gender),
]

def generate_select_answer(question: FormQuestion, profile: dict) -> str:
    options = question.options
    if not options:
        return ""
    
    skip_items = {"seleccionar", "seleccione", "elige", "choose", "select", "",
                  "ninguno", "ninguna", "nada", "none", "no aplica", "n/a"}
    valid_opts = [o for o in options if re.sub(r'[\s\.\,\;\:\-\_]+', '', o.strip().lower()) not in skip_items
                  and o.strip().lower() not in skip_items]
    if not valid_opts:
        valid_opts = options
    first_valid = valid_opts[0]
    
    label_lower = question.label.lower()
    for keywords, matcher in _SELECT_RULES:
        if any(k in label_lower for k in keywords):
            match = matcher(valid_opts, profile)
            if match:
                return match
            
    return first_valid

from engines.selenium_engine import SeleniumEngine
from services.ai_provider import _call_ai, _clean_json
import asyncio

class FormFillerAgent:
    def __init__(self, engine: SeleniumEngine, profile_data: dict, add_log_func=None):
        self.engine = engine
        self.profile_data = profile_data
        self.max_steps = 15
        self.add_log = add_log_func

    async def _log(self, msg: str):
        logger.info(msg)
        if self.add_log:
            await self.add_log(f"[AI Agent] {msg}")

    async def execute(self, job_id: str) -> bool:
        for step in range(self.max_steps):
            await self._log(f"Analizando paso {step+1}/{self.max_steps}...")
            await asyncio.sleep(4)
            
            # Check for success
            try:
                page_text = self.engine.extract("body")
                page_text_lower = " ".join(page_text).lower()
                success_keywords = ["postulación enviada", "application submitted", "successfully applied", "se ha enviado tu solicitud", "ya te has postulado"]
                if any(k in page_text_lower for k in success_keywords):
                    await self._log("¡Mensaje de éxito detectado en la pantalla!")
                    return True
            except Exception:
                pass

            forms = self.engine.get_forms()
            dom_text = "CAMPOS DISPONIBLES:\n"
            inputs_found = 0
            for f in forms:
                for field in f.fields:
                    desc = f"Tag: {field.tag}, Type: {field.type}, Name: {field.name}, Label/Placeholder: {field.label}"
                    dom_text += f"- [{desc}]\n"
                    inputs_found += 1
            if inputs_found == 0:
                dom_text += "(Ninguno)\n"

            try:
                stray_buttons = self.engine.extract("button, a")
                valid_buttons = list(set(b.strip() for b in stray_buttons if b.strip() and len(b.strip()) < 50))[:20]
                dom_text += "\nBOTONES VISIBLES:\n"
                for b in valid_buttons:
                    dom_text += f"- '{b}'\n"
            except Exception:
                pass

            prompt = f"""
Eres un agente llenando una postulación paso a paso.
CV: {json.dumps(self.profile_data, ensure_ascii=False)}

PANTALLA:
{dom_text}

Elige UNA sola acción. Responde SOLO con JSON estricto:
{{
    "action": "click" | "fill" | "upload" | "finish",
    "target": "texto del botón (click) O atributo name/placeholder (fill/upload)",
    "value": "texto a escribir (solo fill)"
}}
"""
            try:
                raw = await _call_ai(prompt)
                json_str = _clean_json(raw)
                if not json_str.startswith("{"):
                    m = re.search(r'\{.*\}', json_str, re.DOTALL)
                    if m:
                        json_str = m.group(0)
                
                data = json.loads(json_str)
                action = data.get("action")
                target = data.get("target")
                val = data.get("value", "")

                await self._log(f"Decisión: {action} | target: {target} | value: {val}")

                if action == "finish":
                    return True
                elif action == "click":
                    await self._log(f"Haciendo click en '{target}'...")
                    await asyncio.to_thread(self.engine.click_by_text, target)
                elif action == "fill":
                    await self._log(f"Llenando campo '{target}' con '{val}'...")
                    target_json = json.dumps(target)
                    val_json = json.dumps(val)
                    js = f"""
                    const ins = document.querySelectorAll('input, textarea');
                    for (let i of ins) {{
                        if (i.name === {target_json} || i.placeholder === {target_json}) {{
                            i.value = {val_json};
                            i.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            return 'ok';
                        }}
                    }}
                    """
                    await asyncio.to_thread(self.engine.run_script, js)
                elif action == "upload":
                    await self._log("Intento de subida de archivo (requiere selector exacto)...")
                    pass # Upload logic is complex via JS without exact path
            except Exception as e:
                await self._log(f"Error parseando respuesta de IA: {e}")

        await self._log("Se alcanzó el límite máximo de pasos sin finalizar.")
        return False
