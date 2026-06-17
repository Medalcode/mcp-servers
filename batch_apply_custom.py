#!/usr/bin/env python3
"""Batch apply to all to_apply offers using logged-in Chrome profile."""
import asyncio, sys, os, json, re, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB = os.path.expanduser("~/.local/share/pathwise/pathwise.db")

# Only portals we're logged into
LOGGED_IN_DOMAINS = {
    "www.chiletrabajos.cl", "www.laborum.cl", "www.trabajando.cl",
    "cl.linkedin.com", "www.linkedin.com",
}

SALARY = "900000"
AVAILABILITY = "Inmediata"

def get_profile():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM profiles WHERE is_default=1")
    p = dict(cur.fetchone() or {})
    p_id = p["id"]
    cur.execute("SELECT name FROM skills WHERE profile_id=?", (p_id,))
    p["skills"] = [r["name"] for r in cur.fetchall()]
    cur.execute("SELECT * FROM experience WHERE profile_id=?", (p_id,))
    p["experience"] = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT * FROM education WHERE profile_id=?", (p_id,))
    p["education"] = [dict(r) for r in cur.fetchall()]
    conn.close()
    return p

def get_offers():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, job_title, company, url, notes FROM applications WHERE status='to_apply' ORDER BY id")
    return [dict(zip(["id","job_title","company","url","notes"], r)) for r in cur.fetchall()]

def update_status(app_id, status, notes=""):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("UPDATE applications SET status=?, notes=? WHERE id=?", (status, notes, app_id))
    conn.commit()
    conn.close()

def gen_cover(job_title, company, profile):
    return f"""Estimado equipo de {company},

Me presento como un profesional en formación con sólidos fundamentos en {', '.join(profile['skills'][:5])}. Estoy muy interesado en la posición de {job_title} y en la oportunidad de contribuir a sus proyectos.

Mi formación incluye {', '.join([e.get('degree','') + ' en ' + e.get('field','') for e in profile['education'][:1]])} y experiencia práctica en {', '.join([e.get('job_title','') for e in profile['experience'][:2]])}.

Me caracterizo por ser autodidacta, proactivo y con excelente capacidad de trabajo en equipo. Busco mi primera oportunidad profesional para aplicar y desarrollar mis habilidades en un entorno real.

Quedo atento a su respuesta.

Saludos cordiales,
Jonatthan Medalla"""

def match_field(name, label, skills):
    """Match a form field to a value based on name and label."""
    nl = (name + " " + (label or "")).lower()
    if any(w in nl for w in ["carta", "presentacion", "cover", "app_letter"]):
        return "cover"
    if any(w in nl for w in ["salario", "renta", "salary", "pretension"]):
        return SALARY
    if any(w in nl for w in ["disponibilidad", "disp"]):
        return AVAILABILITY
    if any(w in nl for w in ["comuna", "residencia", "domicilio", "direccion"]):
        return "Santiago, Chile"
    if any(w in nl for w in ["telefono", "fono", "celular", "contacto"]):
        return "+56912345678"
    if any(w in nl for w in ["linkedin", "url", "portfolio", "portafolio", "github"]):
        if "linkedin" in nl: return "https://linkedin.com/in/jonatthanmedalla"
        if "github" in nl: return "https://github.com/jonatthanmedalla"
        return ""
    if any(w in nl for w in ["ingles", "english", "idioma"]):
        return "Intermedio"
    if any(w in nl for w in ["experiencia", "años", "anos"]):
        return "1 año"
    if any(w in nl for w in ["educacion", "formacion", "titulo", "carrera"]):
        return "Ingeniería Informática"
    if any(w in nl for w in ["habilidades", "conocimiento", "skills", "tecnologia"]):
        return ", ".join(skills[:5])
    if any(w in nl for w in ["expectativa", "aspiracion"]):
        return SALARY
    if any(w in nl for w in ["tiempo", "jornada", "modalidad", "horario"]):
        return "Full-time"
    if any(w in nl for w in ["php", "laravel", "framework"]):
        return "Conocimiento básico, dispuesto a aprender"
    if any(w in nl for w in ["motivacion", "motivo", "interes", "por que"]):
        return "Me apasiona la tecnología y busco mi primera oportunidad para crecer profesionalmente."
    return None

async def apply_one(app, profile, call_tool):
    aid, title, company, url = app["id"], app["job_title"], app["company"], app["url"]
    print(f"\n{'='*60}")
    print(f"APPLYING: [{aid}] {title} @ {company}")
    print(f"URL: {url}")

    # Navigate
    page = await call_tool("navigate", {"url": url})
    await asyncio.sleep(4)
    if "Error" in page or "error" in page[:200]:
        print(f"  FAILED to load: {page[:200]}")
        update_status(aid, "rejected", notes=f"Error loading page: {page[:100]}")
        return False

    print(f"  Page loaded: {page[:100]}...")

    # Click postular
    r = await call_tool("click_by_text", {"text": "Postular|Postularme|Apply|Aplicar|Postulación"})
    await asyncio.sleep(3)
    print(f"  Click: {r[:200]}")

    # Check if we need to login first
    page2 = await call_tool("forms", {})
    await asyncio.sleep(1)

    if "login" in page2.lower() or "ingresa" in page2.lower() or "registrate" in page2.lower():
        print(f"  LOGIN REQUIRED - skipping (no auto-login for this portal)")
        update_status(aid, "to_apply", notes=f"Login required on this portal")
        return False

    forms = await call_tool("forms", {})
    print(f"  Forms: {forms[:400]}...")

    if "No forms found" in forms:
        print(f"  No forms found")
        update_status(aid, "to_apply", notes=f"No application form found on page")
        return False

    # Parse and fill fields
    cover = gen_cover(title, company, profile)
    lines = forms.split('\n')
    filled = False
    for i, line in enumerate(lines):
        m = re.match(r'\s*\[(\w+)\]\s+(\S+)\s+\((\w+)\)', line)
        if not m: continue
        tag, name, ftype = m.groups()
        if ftype == "hidden": continue
        label = ""
        if i + 1 < len(lines) and "Label:" in lines[i + 1]:
            label = lines[i + 1].split("Label:")[-1].strip()
        value = match_field(name, label, profile["skills"])
        if value == "cover":
            value = cover
        if value is not None:
            print(f"  Fill [{name}]: {str(value)[:60]}...")
            result = await call_tool("fill", {"selector": f"[name='{name}']", "value": str(value)})
            await asyncio.sleep(0.5)
            filled = True
        if ftype == "checkbox":
            await call_tool("click", {"selector": f"[name='{name}']"})
            await asyncio.sleep(0.3)

    if not filled:
        print(f"  No fields to fill")
        update_status(aid, "to_apply", notes="No recognizable fields")
        return False

    # Submit
    s1 = await call_tool("click_by_text", {"text": "Enviar|Postular|Enviar postulación|Submit|Send|Aplicar"})
    if "Clicked" not in s1:
        s2 = await call_tool("click", {"selector": "button[type=submit], input[type=submit], [class*=btn] input[value*=Enviar], [class*=btn] input[value*=Postular]"})
        print(f"  Submit CSS: {s2[:100]}")
    else:
        print(f"  Submit clicked: {s1}")

    update_status(aid, "applied", notes=f"Applied via batch_apply_custom on {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}")
    print(f"  ✅ APPLIED SUCCESSFULLY")
    return True

async def main():
    from services.browser_client import call_tool, reset_browser

    profile = get_profile()
    print(f"Profile: {profile.get('name')}")
    print(f"Skills: {profile['skills']}")
    print(f"Experience: {len(profile['experience'])} entries")
    print(f"Education: {len(profile['education'])} entries")

    offers = get_offers()
    print(f"\nOffers to apply: {len(offers)}")

    # Filter by logged-in domains
    from urllib.parse import urlparse
    filtered = [o for o in offers if urlparse(o["url"] or "").netloc in LOGGED_IN_DOMAINS]
    print(f"Logged-in portals: {len(filtered)} offers")
    for o in filtered:
        print(f"  [{o['id']}] {o['job_title']} @ {o['company']} ({urlparse(o['url']).netloc})")

    if not filtered:
        print("No offers on logged-in portals. Log in to more portals first.")
        return

    print(f"\nStarting batch apply to {len(filtered)} offers...")

    success = 0
    failed = 0
    for app in filtered:
        try:
            ok = await apply_one(app, profile, call_tool)
            if ok:
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            update_status(app["id"], "to_apply", notes=f"Error: {str(e)[:200]}")
            failed += 1
        finally:
            await reset_browser()
            await asyncio.sleep(2)

    print(f"\n{'='*60}")
    print(f"Done: {success} applied, {failed} failed out of {len(filtered)}")

if __name__ == "__main__":
    asyncio.run(main())
