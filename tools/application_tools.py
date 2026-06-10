from mcp.server import FastMCP
from database.repos import applications as app_repo

def register_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def application_list(status: str = None) -> str:
        """List all job applications, optionally filtered by status (to_apply, applied, interview, offer, rejected)."""
        apps = app_repo.list_applications(status=status)
        if not apps:
            return "No applications found."
        import json
        return json.dumps(apps, indent=2, ensure_ascii=False)

    @mcp.tool()
    async def application_get(application_id: int) -> str:
        """Get details of a specific job application by its ID."""
        app = app_repo.get_application(application_id)
        if not app:
            return f"Application {application_id} not found."
        import json
        return json.dumps(dict(app), indent=2, ensure_ascii=False)

    @mcp.tool()
    async def application_create(job_title: str, company: str, url: str = None, status: str = "to_apply",
                                  profile_id: int = None, salary_range: str = None,
                                  location: str = None, notes: str = None) -> str:
        """Track a new job application with job title, company name, and optional details like URL, salary range, and notes."""
        app_id = app_repo.create_application(1, job_title, company, url, status,
                                              profile_id, salary_range, location, notes)
        return f"Application created with ID {app_id} for {job_title} at {company}."

    @mcp.tool()
    async def application_update(application_id: int, job_title: str = None, company: str = None,
                                  url: str = None, status: str = None, salary_range: str = None,
                                  location: str = None, notes: str = None) -> str:
        """Update an existing job application's details like title, company, status, URL, salary range, location, or notes."""
        fields = {"job_title": job_title, "company": company, "url": url, "status": status,
                  "salary_range": salary_range, "location": location, "notes": notes}
        kwargs = {k: v for k, v in fields.items() if v is not None}
        ok = app_repo.update_application(application_id, 1, **kwargs)
        return f"Application {application_id} updated." if ok else f"Application {application_id} not found."

    @mcp.tool()
    async def application_update_status(application_id: int, status: str) -> str:
        """Quickly change the status of an application. Valid statuses: to_apply, applied, interview, offer, rejected."""
        valid = ["to_apply", "applied", "interview", "offer", "rejected"]
        if status not in valid:
            return f"Invalid status. Valid: {', '.join(valid)}"
        ok = app_repo.patch_status(application_id, 1, status)
        return f"Status updated to '{status}'." if ok else f"Application {application_id} not found."

    @mcp.tool()
    async def application_delete(application_id: int) -> str:
        """Delete a job application entry by its ID."""
        ok = app_repo.delete_application(application_id)
        return f"Application {application_id} deleted." if ok else f"Application {application_id} not found."

    @mcp.tool()
    async def application_stats() -> str:
        """Get application statistics: total apps, count by status, response rate, and applications this week."""
        import json
        return json.dumps(app_repo.get_stats(), indent=2, ensure_ascii=False)
