from mcp.server import FastMCP
from database.repos import profiles as profile_repo

def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def profile_load(profile_id: int = None) -> str:
        """Load your professional profile (skills, experience, education). Returns full profile data with all fields."""
        if profile_id:
            data = profile_repo.get_full_profile(profile_id)
        else:
            data = profile_repo.get_default_profile()
        if not data:
            return "No profile found. Create one with profile_save first."
        import json
        return json.dumps(data, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def profile_list() -> str:
        """List all saved professional profiles with their IDs, names, and types."""
        profiles = profile_repo.list_profiles()
        if not profiles:
            return "No profiles found."
        import json
        return json.dumps(profiles, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def profile_save(name: str, title: str = "", summary: str = "", skills: list[str] | None = None) -> str:
        """Create a new professional profile with a name, optional title, summary, and skills list."""
        profile = profile_repo.create_profile(1, name, "professional", title=title, summary=summary, skills=skills or [])
        if profile:
            return f"Profile '{name}' created with ID {profile['id']}."
        return "Failed to create profile."

    @mcp.tool()
    async def profile_delete(profile_id: int) -> str:
        """Delete a profile by its ID. Cannot delete the only remaining profile."""
        try:
            profile_repo.delete_profile(profile_id)
            return f"Profile {profile_id} deleted."
        except ValueError as e:
            return str(e)

    @mcp.tool()
    async def profile_generate_personas() -> str:
        """Generate 3 optimized professional profiles (personas) from your base profile using AI, targeting different roles."""
        data = profile_repo.get_default_profile()
        if not data:
            return "No default profile found."
        from services.ai_provider import generate_personas
        personas = await generate_personas(data)
        import json
        return json.dumps(personas, indent=2, ensure_ascii=False)
