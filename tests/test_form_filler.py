import json
from services.form_filler import (
    parse_forms_json,
    generate_answer,
    generate_radio_answer,
    generate_select_answer,
    QuestionType,
    FormQuestion,
    _infer_type,
    _normalize_label,
)


class TestInferType:
    def test_textarea(self):
        assert _infer_type("textarea", "") == QuestionType.TEXTAREA

    def test_select(self):
        assert _infer_type("select", "") == QuestionType.SELECT

    def test_email(self):
        assert _infer_type("input", "email") == QuestionType.EMAIL

    def test_tel(self):
        assert _infer_type("input", "tel") == QuestionType.TEL

    def test_default_text(self):
        assert _infer_type("input", "color") == QuestionType.TEXT


class TestNormalizeLabel:
    def test_trim_spaces(self):
        assert _normalize_label("  hola  mundo  ") == "hola mundo"

    def test_remove_question_marks(self):
        assert _normalize_label("¿Tienes experiencia?") == "Tienes experiencia"

    def test_keep_normal_text(self):
        assert _normalize_label("Nombre completo") == "Nombre completo"


class TestParseFormsJson:
    def test_empty(self):
        assert parse_forms_json("[]") == []
        assert parse_forms_json("{}") == []

    def test_single_field(self):
        data = json.dumps({"fields": [{"tag": "input", "type": "email", "name": "correo", "label": "Correo electrónico"}]})
        questions = parse_forms_json(data)
        assert len(questions) == 1
        assert questions[0].type == QuestionType.EMAIL
        assert questions[0].name == "correo"

    def test_hidden_skipped(self):
        data = json.dumps({"fields": [
            {"tag": "input", "type": "hidden", "name": "token"},
            {"tag": "input", "type": "text", "name": "name", "label": "Nombre"},
        ]})
        questions = parse_forms_json(data)
        assert len(questions) == 1
        assert questions[0].name == "name"

    def test_select_field(self):
        data = json.dumps({"fields": [{"tag": "select", "name": "ciudad", "label": "Ciudad"}]})
        questions = parse_forms_json(data)
        assert len(questions) == 1
        assert questions[0].type == QuestionType.SELECT

    def test_textarea_field(self):
        data = json.dumps({"fields": [{"tag": "textarea", "name": "desc", "label": "Descripción"}]})
        questions = parse_forms_json(data)
        assert len(questions) == 1
        assert questions[0].type == QuestionType.TEXTAREA

    def test_radio_field(self):
        data = json.dumps({"fields": [{"tag": "input", "type": "radio", "name": "disponibilidad", "label": "Disponibilidad"}]})
        questions = parse_forms_json(data)
        assert len(questions) == 1
        assert questions[0].type == QuestionType.RADIO

    def test_text_fallback(self):
        result = parse_forms_json("some random text")
        assert isinstance(result, list)

    def test_double_json(self):
        inner = json.dumps({"fields": [{"tag": "input", "type": "text", "name": "n", "label": "N"}]})
        result = parse_forms_json(json.dumps(inner))
        assert len(result) == 1


class TestGenerateAnswer:
    def test_email_field(self, sample_profile):
        q = FormQuestion(QuestionType.EMAIL, "Correo electrónico", "email")
        assert generate_answer(q, sample_profile) == "juan@example.com"

    def test_phone_field(self, sample_profile):
        q = FormQuestion(QuestionType.TEL, "Teléfono", "phone")
        assert generate_answer(q, sample_profile) == "+56912345678"

    def test_education_keyword(self, sample_profile):
        q = FormQuestion(QuestionType.TEXTAREA, "Formación académica", "edu")
        result = generate_answer(q, sample_profile)
        assert "U. de Chile" in result

    def test_skills_keyword(self, sample_profile):
        q = FormQuestion(QuestionType.TEXTAREA, "Conocimientos técnicos", "tech")
        result = generate_answer(q, sample_profile)
        assert "Python" in result
        assert "JavaScript" in result

    def test_salary_keyword(self, sample_profile):
        q = FormQuestion(QuestionType.TEXT, "Pretensión de renta", "sueldo")
        result = generate_answer(q, sample_profile)
        assert result is not None
        assert len(str(result)) > 0

    def test_fallback_answer(self, sample_profile):
        q = FormQuestion(QuestionType.TEXTAREA, "Comentarios adicionales", "comments")
        result = generate_answer(q, sample_profile)
        assert "Sí" in result
        assert "Full Stack" in result


class TestGenerateRadioAnswer:
    def test_disponibilidad_returns_si(self, sample_profile):
        q = FormQuestion(QuestionType.RADIO, "¿Tienes disponibilidad inmediata?", "disp")
        assert generate_radio_answer(q, sample_profile) == "Sí"

    def test_negative_pattern_returns_no(self, sample_profile):
        q = FormQuestion(QuestionType.RADIO, "¿Tienes alguna discapacidad?", "disc")
        assert generate_radio_answer(q, sample_profile) == "No"

    def test_default_returns_si(self, sample_profile):
        q = FormQuestion(QuestionType.RADIO, "¿Alguna pregunta?", "gen")
        assert generate_radio_answer(q, sample_profile) == "Sí"


class TestGenerateSelectAnswer:
    def test_city_match(self, sample_profile):
        q = FormQuestion(QuestionType.SELECT, "Comuna", "comuna", options=["Santiago", "Providencia", "Las Condes"])
        assert generate_select_answer(q, sample_profile) == "Santiago"

    def test_city_fallback(self, sample_profile):
        q = FormQuestion(QuestionType.SELECT, "Comuna", "comuna", options=["Providencia", "Las Condes"])
        ans = generate_select_answer(q, sample_profile)
        assert ans in ("Providencia", "Las Condes")

    def test_country_match(self, sample_profile):
        q = FormQuestion(QuestionType.SELECT, "País", "pais", options=["Perú", "Chile", "Argentina"])
        assert generate_select_answer(q, sample_profile) == "Chile"

    def test_no_options(self, sample_profile):
        q = FormQuestion(QuestionType.SELECT, "País", "pais", options=[])
        assert generate_select_answer(q, sample_profile) == ""

    def test_default_to_first(self, sample_profile):
        q = FormQuestion(QuestionType.SELECT, "Género", "genero", options=["Masculino", "Femenino", "Otro"])
        assert generate_select_answer(q, sample_profile) == "Masculino"
