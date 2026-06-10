from mcp.server import FastMCP
from services.job_service import search_jobs, search_jobs_with_ai
from database.repos import profiles as profile_repo

def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def job_search(query: str, location: str = "Chile", remote_only: bool = False,
                          use_ai: bool = False) -> str:
        """Search jobs across 7 job boards (ChileTrabajos, CompuTrabajo, Laborum, Indeed, GetOnBoard, Trabajando.cl, RemoteOK). Set use_ai=true for AI-powered matching using your profile."""
        if use_ai:
            profile = profile_repo.get_default_profile()
            if profile:
                jobs = await search_jobs_with_ai(query, profile, location, remote_only)
            else:
                jobs = await search_jobs(query, location, remote_only)
        else:
            jobs = await search_jobs(query, location, remote_only)

        if not jobs:
            return "No jobs found. Try different keywords or location."

        import json
        display = min(len(jobs), 25)
        result = {
            "count": len(jobs),
            "displayed": display,
            "warning": f"Mostrando {display} de {len(jobs)} resultados. Refina tu búsqueda para ver más." if len(jobs) > 25 else None,
            "query": query,
            "location": location,
            "remoteOnly": remote_only,
            "aiMatched": use_ai,
            "jobs": jobs[:25],
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def job_search_from_profile(profile_id: int = None, remote_only: bool = False,
                                       use_ai: bool = True, location: str = "Chile") -> str:
        """Search jobs using your profile's title and skills. AI matching is enabled by default for smarter results."""
        if profile_id:
            data = profile_repo.get_full_profile(profile_id)
        else:
            data = profile_repo.get_default_profile()
        if not data:
            return "No profile found."

        pi = data.get("personalInfo", {})
        title = pi.get("currentTitle", "") or "developer"
        skills = data.get("skills", [])
        query = f"{title} {' '.join(skills[:5])}"

        if use_ai:
            jobs = await search_jobs_with_ai(query, data, location=location, remote_only=remote_only)
        else:
            jobs = await search_jobs(query, location=location, remote_only=remote_only)

        if not jobs:
            return "No jobs found matching your profile."

        import json
        display = min(len(jobs), 25)
        result = {
            "count": len(jobs),
            "displayed": display,
            "warning": f"Mostrando {display} de {len(jobs)} resultados. Refina tu búsqueda para ver más." if len(jobs) > 25 else None,
            "query": query,
            "profileUsed": data.get("personalInfo", {}).get("firstName", ""),
            "aiMatched": use_ai,
            "jobs": jobs[:25],
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
