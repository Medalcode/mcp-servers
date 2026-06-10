from datetime import datetime, timedelta
from mcp.server import FastMCP
from services.company_research import research_company as rc, get_company_insights
from services.ai_provider import _call_ai
from database.repos import applications as app_repo
from database.repos import profiles as profile_repo
from database import get_connection
import logging

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def company_research(company_name: str) -> str:
        """Research a company: website, industry, size, culture, tech stack, and career page URL."""
        insights = await get_company_insights(company_name)
        return insights

    @mcp.tool()
    async def interview_prepare(application_id: int) -> str:
        """Generate interview preparation materials for a specific application. Creates questions, talking points, and research notes."""
        app = app_repo.get_application(application_id)
        if not app:
            return f"Application {application_id} not found."

        company_info = await rc(app["company"])

        profile = profile_repo.get_default_profile()
        profile_text = ""
        if profile:
            pi = profile.get("personalInfo", {})
            skills = ", ".join(profile.get("skills", []))
            exp = profile.get("experience", [])
            exp_text = "; ".join(f"{e['title']} en {e['company']}" for e in exp[:3])
            profile_text = f"Perfil: {pi.get('currentTitle', '')}\nExperiencia: {exp_text}\nHabilidades: {skills}"

        prompt = f"""Genera materiales de preparación para una entrevista para:

Puesto: {app['job_title']}
Empresa: {app['company']}
{profile_text}

Información de la empresa:
- Industria: {company_info.get('industry', '')}
- Descripción: {company_info.get('description', '')}
- Stack: {company_info.get('tech_stack', '')}
- Cultura: {company_info.get('culture', '')}

Genera en español:
1. 5 preguntas técnicas probables con respuestas
2. 5 preguntas conductuales (STAR) con respuestas
3. 3 talking points sobre por qué eres buen fit
4. 3 preguntas para hacerle al entrevistador

Responde en formato markdown."""
        try:
            result = await _call_ai(prompt)
        except Exception as e:
            result = f"Error generando preparación: {e}"

        conn = get_connection()
        conn.execute(
            "INSERT INTO interview_questions (application_id, company, job_title, question_type, question, answer) VALUES (?,?,?,?,?,?)",
            (application_id, app["company"], app["job_title"], "preparation",
             f"Entrevista para {app['job_title']}", result[:1000])
        )
        conn.commit()

        return result

    @mcp.tool()
    async def search_applications(query: str) -> str:
        """Full-text search across your job applications. Search by title, company name, or notes."""
        conn = get_connection()
        try:
            cur = conn.execute(
                """SELECT id, job_title, company, status, location, applied_date
                   FROM applications_fts WHERE applications_fts MATCH ?
                   ORDER BY rank LIMIT 20""",
                (query,)
            )
            results = cur.fetchall()
            if not results:
                # Fall back to LIKE search
                like = f"%{query}%"
                cur = conn.execute(
                    """SELECT id, job_title, company, status, location, applied_date
                       FROM applications WHERE job_title LIKE ? OR company LIKE ? OR notes LIKE ?
                       ORDER BY created_at DESC LIMIT 20""",
                    (like, like, like)
                )
                results = cur.fetchall()
        except Exception:
            like = f"%{query}%"
            cur = conn.execute(
                """SELECT id, job_title, company, status, location, applied_date
                   FROM applications WHERE job_title LIKE ? OR company LIKE ? OR notes LIKE ?
                   ORDER BY created_at DESC LIMIT 20""",
                (like, like, like)
            )
            results = cur.fetchall()

        if not results:
            return "No applications match your search."

        lines = [f"=== Resultados para '{query}' ==="]
        for r in results:
            lines.append(f"  #{r['id']} {r['job_title'][:40]} @ {r['company'][:20]} - {r['status']} ({r['applied_date'][:10]})")
        return "\n".join(lines)

    @mcp.tool()
    async def get_weekly_report() -> str:
        """Generate a weekly job search activity report with stats, top matches, and pending follow-ups."""
        stats = app_repo.get_stats()
        apps = app_repo.list_applications()

        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        this_week = [a for a in apps if str(a.get("applied_date", ""))[:10] >= week_ago]
        pending = [a for a in apps if a.get("status") in ("to_apply", "applied")]

        today = datetime.now().strftime("%Y-%m-%d")
        week_start = (datetime.now() - timedelta(days=7)).strftime("%d-%m-%Y")
        lines = [
            "=== REPORTE SEMANAL DE BÚSQUEDA ===",
            f"Período: {week_start} a {today}",
            "",
            f"Total aplicaciones: {stats['total']}",
            f"Postuladas: {stats['by_status'].get('applied', 0)}",
            f"En entrevista: {stats['by_status'].get('interview', 0)}",
            f"Ofertas: {stats['by_status'].get('offer', 0)}",
            f"Rechazadas: {stats['by_status'].get('rejected', 0)}",
            f"Pendientes: {stats['by_status'].get('to_apply', 0)}",
            f"Tasa de respuesta: {stats['response_rate']}%",
            f"Aplicaciones esta semana: {stats['this_week']}",
            "",
            f"--- Postulaciones recientes ({len(this_week)} en la última semana) ---",
        ]

        for a in this_week[:10]:
            lines.append(f"  {a['job_title'][:40]} @ {a['company'][:20]} - {a['status']}")

        lines.append(f"\n--- Pendientes de seguimiento ({len(pending)} total) ---")
        for a in pending[:5]:
            lines.append(f"  #{a['id']} {a['job_title'][:35]} @ {a['company'][:15]}")

        return "\n".join(lines)
