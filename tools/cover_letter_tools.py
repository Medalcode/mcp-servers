from mcp.server import FastMCP
from database.repos import profiles as profile_repo
from services.ai_provider import generate_cover_letter

def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def cover_letter_generate(job_title: str, company: str, job_description: str,
                                     tone: str = "professional", profile_id: int = None) -> str:
        """Generate a tailored cover letter for a specific job. Provide the job title, company name, and full job description. Optional tone: professional, casual, or technical."""
        if profile_id:
            data = profile_repo.get_full_profile(profile_id)
        else:
            data = profile_repo.get_default_profile()
        if not data:
            return "No profile found. Save a profile first."
        letter = await generate_cover_letter(data, job_title, company, job_description, tone)
        return letter

    @mcp.tool()
    async def cover_letter_suggest_improvements(cover_letter: str, job_description: str) -> str:
        """Analyze a cover letter and job description, then suggest improvements to make the letter more effective."""
        from services.ai_provider import _call_routemcp
        prompt = f"""Analiza esta carta de presentación y la descripción del trabajo. Sugiere mejoras específicas para que la carta sea más efectiva.

CARTA:
{cover_letter}

DESCRIPCIÓN DEL TRABAJO:
{job_description}

Sugiere 3-5 mejoras concretas. Responde en español."""
        try:
            result = await _call_routemcp("cover_letter_improve", prompt)
            return result
        except Exception as e:
            return f"Error: {e}"
