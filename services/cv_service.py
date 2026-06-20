import re
from pathlib import Path

try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

_ALLOWED_DIRS = [
    Path.home() / "Escritorio",
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path.cwd(),
    Path("/tmp/opencode"),
]

async def parse_pdf(file_path: str) -> dict:
    path = Path(file_path).resolve()
    allowed = any(
        str(path).startswith(str(d.resolve()))
        for d in _ALLOWED_DIRS if d.exists()
    )
    if not allowed:
        raise PermissionError(f"Access denied: {file_path} is outside allowed directories")
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = ""
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(str(path))
        except fitz.FileDataError as e:
            if "encrypted" in str(e).lower() or "password" in str(e).lower():
                raise ValueError("Cannot open encrypted/password-protected PDF")
            raise
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
    elif HAS_PYPDF2:
        try:
            reader = PdfReader(str(path))
        except Exception as e:
            if "encrypted" in str(e).lower() or "password" in str(e).lower():
                raise ValueError("Cannot open encrypted/password-protected PDF")
            raise
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise RuntimeError("No PDF library available. Install pymupdf or pypdf2.")

    return {"text": text.strip(), "pages": len(text.split("\n\n"))}

def parse_cv_text(text: str) -> dict:
    data = {
        "personalInfo": {},
        "experience": [],
        "education": [],
        "skills": [],
    }

    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n") if ln.strip()]

    email_m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    if email_m:
        data["personalInfo"]["email"] = email_m.group(0)

    phone_m = re.search(r"(\+?\d{1,3}\s?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", text)
    if phone_m:
        data["personalInfo"]["phone"] = phone_m.group(0).strip()

    for i in range(min(5, len(lines))):
        if 5 < len(lines[i]) < 50 and "@" not in lines[i] and not lines[i].startswith("+"):
            parts = [p for p in lines[i].split() if len(p) > 1]
            if 2 <= len(parts) <= 6:
                data["personalInfo"]["firstName"] = parts[0]
                data["personalInfo"]["lastName"] = " ".join(parts[1:])
                break

    linkedin_m = re.search(r"linkedin\.com/in/[\w-]+", text, re.I)
    if linkedin_m:
        data["personalInfo"]["linkedin"] = "https://" + linkedin_m.group(0)

    github_m = re.search(r"github\.com/[\w-]+", text, re.I)
    if github_m:
        data["personalInfo"]["github"] = "https://" + github_m.group(0)

    location_m = re.search(r"(Santiago|Buenos Aires|Lima|Bogotá|México|Madrid|Barcelona),\s*(Chile|Argentina|Perú|Colombia|México|España)", text)
    if location_m:
        data["personalInfo"]["city"] = location_m.group(1).strip()
        data["personalInfo"]["country"] = location_m.group(2).strip()

    skill_categories = {
        "Lenguajes": [
            "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Ruby", "PHP",
            "Go", "Golang", "Rust", "Swift", "Kotlin", "Scala", "Perl", "R",
            "Dart", "Elixir", "Haskell", "Clojure", "Lua", "Julia", "Shell", "Bash",
            "C", "HTML", "CSS", "SASS", "LESS", "GraphQL",
        ],
        "Frameworks Backend": [
            "Django", "Flask", "FastAPI", "Express", "Spring Boot", "Spring",
            "ASP.NET", "Ruby on Rails", "Laravel", "Symfony", "NestJS",
            "Next.js", "Nuxt.js", "Phoenix", "Play Framework", "Micronaut",
            "Quarkus", "Fiber", "Echo", "Gin",
        ],
        "Frameworks Frontend": [
            "React", "Vue.js", "Angular", "Svelte", "SolidJS", "Preact",
            "jQuery", "Backbone", "Ember", "Alpine.js", "Stimulus",
            "Tailwind", "Bootstrap", "Material UI", "Shadcn", "Chakra UI",
            "Ant Design", "Styled Components", "CSS Modules",
        ],
        "Bases de Datos": [
            "PostgreSQL", "MySQL", "MariaDB", "SQLite", "Oracle", "SQL Server",
            "MongoDB", "Redis", "Elasticsearch", "Cassandra", "DynamoDB",
            "Firebase", "Supabase", "CouchDB", "Neo4j", "InfluxDB",
            "TimescaleDB", "ClickHouse", "BigQuery", "Redshift", "Snowflake",
        ],
        "DevOps y Cloud": [
            "Docker", "Kubernetes", "K8s", "AWS", "Azure", "GCP", "Google Cloud",
            "Terraform", "Ansible", "Pulumi", "Jenkins", "GitLab CI", "GitHub Actions",
            "CircleCI", "Travis CI", "ArgoCD", "Helm", "Istio", "Prometheus",
            "Grafana", "Datadog", "New Relic", "Sentry", "Cloudflare", "Nginx",
            "Apache", "HAProxy", "Vagrant", "Packer", "Nomad", "Consul", "Vault",
        ],
        "Datos y BI": [
            "Power BI", "Tableau", "Looker", "Airflow", "Spark", "Hadoop",
            "Kafka", "Flink", "Beam", "Pandas", "NumPy", "SciPy", "Scikit-learn",
            "TensorFlow", "PyTorch", "Jupyter", "Databricks", "dbt", "Snowflake",
            "Redshift", "BigQuery", "SAP", "SAP HANA", "Excel", "VBA",
            "SSIS", "SSAS", "SSRS", "ETL", "Data Warehouse", "Data Lake",
        ],
        "Herramientas": [
            "Git", "Linux", "VS Code", "IntelliJ", "PyCharm", "WebStorm",
            "Vim", "Neovim", "Postman", "Insomnia", "Swagger", "OpenAPI",
            "Jira", "Confluence", "Notion", "Slack", "Trello", "Asana",
            "Figma", "Adobe XD", "Photoshop", "Illustrator",
            "Agile", "Scrum", "Kanban", "SAFe", "ITIL",
        ],
        "Sistemas Operativos": [
            "Linux", "Ubuntu", "Debian", "Red Hat", "CentOS", "Alpine",
            "Windows Server", "macOS", "Unix", "FreeBSD", "OpenBSD",
        ],
        "Redes y Seguridad": [
            "Cisco", "CCNA", "Firewall", "VPN", "SSL", "TLS", "OAuth",
            "OAuth2", "JWT", "LDAP", "Active Directory", "SAML",
            "OWASP", "Penetration Testing", "Wireshark", "Kali Linux",
            "Metasploit", "Burp Suite", "Nmap", "Zabbix", "Nagios",
        ],
        "Mensajeria y Streams": [
            "RabbitMQ", "Kafka", "ActiveMQ", "SQS", "SNS", "NATS",
            "Redis Pub/Sub", "WebSocket", "gRPC", "ZeroMQ", "Pulsar",
        ],
        "Testing": [
            "pytest", "Selenium", "Cypress", "Playwright", "Jest", "Mocha",
            "Chai", "JUnit", "Mockito", "Unittest", "Robot Framework",
            "Cucumber", "Gatling", "k6", "Locust", "Postman",
            "TDD", "BDD", "Integration Testing", "E2E Testing",
        ],
    }
    seen = set()
    for category, skills in skill_categories.items():
        for skill in skills:
            if skill in seen:
                continue
            seen.add(skill)
            if re.search(rf"\b{re.escape(skill)}\b", text, re.I):
                data["skills"].append(skill)

    return data

async def tailor_cv_pdf(base_profile: dict, job_description: str, out_path: str = "/tmp/opencode/tailored_cv.pdf") -> str:
    from services.ai_provider import _call_ai, _clean_json
    import json
    import os
    
    prompt = f"""Reescribe este CV para que haga "match" perfecto con la oferta laboral. Mantén la verdad pero resalta las keywords relevantes.
    PERFIL BASE:
    {json.dumps(base_profile, ensure_ascii=False)}
    OFERTA:
    {job_description[:2000]}
    
    Devuelve ÚNICAMENTE un JSON con este formato:
    {{
        "personalInfo": {{"firstName": "", "lastName": "", "currentTitle": "", "email": "", "phone": "", "summary": ""}},
        "experience": [{{"title": "", "company": "", "description": ""}}],
        "education": [{{"degree": "", "school": ""}}],
        "skills": ["skill1", "skill2"]
    }}
    """
    try:
        res = await _call_ai(prompt)
        tailored = json.loads(_clean_json(res))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("AI Tailoring failed: %s", e)
        tailored = base_profile
        
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        import logging
        logging.getLogger(__name__).error("reportlab is not installed. Returning original path or None.")
        return ""
        
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    c = canvas.Canvas(out_path, pagesize=letter)
    y = 750
    pi = tailored.get("personalInfo", {})
    
    c.setFont("Helvetica-Bold", 16)
    name = f"{pi.get('firstName') or ''} {pi.get('lastName') or ''}"
    c.drawString(50, y, name)
    y -= 20
    
    c.setFont("Helvetica", 12)
    c.drawString(50, y, str(pi.get("currentTitle") or ""))
    y -= 20
    c.drawString(50, y, f"{pi.get('email') or ''} | {pi.get('phone') or ''}")
    y -= 30
    
    c.setFont("Helvetica-Oblique", 10)
    summary = str(pi.get("summary") or "")
    for line in [summary[i:i+90] for i in range(0, len(summary), 90)]:
        c.drawString(50, y, line)
        y -= 15
    y -= 20
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Experiencia")
    y -= 20
    c.setFont("Helvetica", 10)
    for exp in tailored.get("experience") or []:
        title = str(exp.get('title') or '')
        company = str(exp.get('company') or '')
        c.drawString(50, y, f"{title} en {company}")
        y -= 15
        desc = str(exp.get("description") or "")
        for line in [desc[i:i+90] for i in range(0, len(desc), 90)]:
            c.drawString(60, y, "- " + line)
            y -= 15
        y -= 10
        if y < 100:
            c.showPage()
            y = 750
            
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Habilidades")
    y -= 20
    c.setFont("Helvetica", 10)
    skills_list = tailored.get("skills") or []
    skills = ", ".join([str(s or '') for s in skills_list])
    for line in [skills[i:i+90] for i in range(0, len(skills), 90)]:
        c.drawString(50, y, line)
        y -= 15
        
    c.save()
    return out_path
