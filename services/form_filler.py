import re
import json
import logging
from enum import Enum
from typing import Optional

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
            questions.append(FormQuestion(
                qtype=qtype,
                label=found,
                name=name,
                required=required,
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


def _extract_textarea_questions(driver, textareas) -> list[FormQuestion]:
    questions = []
    for ta in textareas:
        label = ""
        try:
            label = driver.execute_script("""
                var el = arguments[0];
                var div = el.closest('div');
                if (!div) return '';
                var text = '';
                var children = div.childNodes;
                for (var i = 0; i < children.length; i++) {
                    if (children[i] === el) break;
                    if (children[i].nodeType === 3 && children[i].textContent.trim()) {
                        text += children[i].textContent.trim() + ' ';
                    } else if (children[i].nodeType === 1 && 
                               !children[i].matches('textarea, input, select, br, hr')) {
                        text += children[i].textContent.trim() + ' ';
                    }
                }
                return text.trim();
            """, ta)
        except Exception as e:
            logger.warning("Error extracting textarea label: %s", e)
        name = ""
        try:
            name = ta.get_attribute("name") or ""
        except Exception as e:
            logger.warning("Error extracting textarea name: %s", e)
        q = FormQuestion(QuestionType.TEXTAREA, label, name)
        questions.append(q)
    return questions


def generate_answer(question: FormQuestion, profile: dict) -> str:
    label_lower = question.label.lower()
    pi = profile.get("personalInfo", {})

    email = pi.get("email", "")
    phone = pi.get("phone", "")
    city = pi.get("city", "")
    name = f"{pi.get('firstName', '')} {pi.get('lastName', '')}".strip() or ""
    skills = ", ".join(profile.get("skills", [])[:10])
    current_title = pi.get("currentTitle", "")
    summary = pi.get("summary", "")
    
    exp_lines = []
    for e in profile.get("experience", [])[:3]:
        desc = (e.get("description") or "")[:200]
        exp_lines.append(f"- {e['title']} en {e['company']}: {desc}")
    exp_text = "\n".join(exp_lines)
    
    edu_lines = []
    for e in profile.get("education", []):
        status = "en curso" if e.get("current") else "completado"
        edu_lines.append(f"- {e['degree']} en {e['school']} ({status})")
    edu_text = "\n".join(edu_lines)

    patterns = [
        (r'(carrera|estudiando|semestre|año|estudios|formación académica|casa de estudios|universidad)',
         f"{edu_text}" if edu_text else "Formación según perfil."),
        (r'(horas|disponibilidad|práctica|full time|comenzar|inicio|jornada)',
         f"Disponibilidad según lo requerido."),
        (r'(teléfono|correo|contacto|número|email)',
         f"{'Teléfono: ' + phone if phone else ''}{' | ' if phone and email else ''}{'Correo: ' + email if email else 'Datos de contacto en el perfil.'}"),
        (r'(experiencia|trayectoria|años)',
         f"{exp_text}" if exp_text else "Experiencia detallada en el perfil."),
        (r'(motivación|interés|por qué)',
         f"Me interesa esta oportunidad para aplicar mis conocimientos y seguir creciendo profesionalmente."),
        (r'(comuna|residencia|vives|vive|domicilio|lugar)',
         f"{'Santiago, ' if city else ''}{city}".strip() or "Según perfil."),
        (r'(portfolio|github|linkedin|enlace)',
         f"{'GitHub: ' + pi.get('github', '') if pi.get('github') else ''}{' | ' if pi.get('github') and pi.get('linkedin') else ''}{'LinkedIn: ' + pi.get('linkedin', '') if pi.get('linkedin') else 'Datos en el perfil.'}"),
        (r'(conocimiento|tecnología|stack|técnico)',
         f"{skills}" if skills else "Según perfil profesional."),
        (r'(sueldo|salario|renta|pretensión)',
         profile.get("personalInfo", {}).get("salary_expectation", "800000")),
    ]

    for pattern, answer in patterns:
        if re.search(pattern, label_lower):
            return answer

    if question.type == QuestionType.EMAIL:
        return email
    if question.type == QuestionType.TEL:
        return phone

    return f"Sí, cuento con la experiencia y formación requerida. {current_title} con conocimientos en {skills}."


def generate_radio_answer(question: FormQuestion, profile: dict) -> str:
    label_lower = question.label.lower()
    
    positive_patterns = [
        r'(disponibilidad|puedes|puede|cuentas|cuenta|tienes|tiene|conocimiento|experiencia)',
        r'(power bi|excel|base de datos|sql|python|programación|análisis)',
        r'(práctica profesional|full time|tiempo completo|presencial|remoto)',
        r'(seguro escolar|seguro)',
    ]
    
    for pattern in positive_patterns:
        if re.search(pattern, label_lower):
            return "Si"
    
    negative_patterns = [
        r'^(no\s|no )',
        r'(discapacidad|enfermedad|problema)',
    ]
    
    for pattern in negative_patterns:
        if re.search(pattern, label_lower):
            return "No"
    
    return "Si"


def generate_select_answer(question: FormQuestion, profile: dict) -> str:
    options = question.options
    if not options:
        return ""
    label_lower = question.label.lower()
    
    if any(t in label_lower for t in ["comuna", "ciudad", "región", "region"]):
        city = profile.get("personalInfo", {}).get("city", "Santiago")
        for opt in options:
            if city.lower() in opt.lower() or opt.lower() in city.lower():
                return opt
        if options:
            return options[0]
    
    if any(t in label_lower for t in ["país", "pais"]):
        for opt in options:
            if "chile" in opt.lower():
                return opt
        if options:
            return options[0]
    
    if options:
        return options[0]
    return ""
