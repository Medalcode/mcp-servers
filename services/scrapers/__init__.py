from services.scrapers.chiletrabajos import scan_chiletrabajos
from services.scrapers.computrabajo import scan_computrabajo
from services.scrapers.getonboard import scan_getonboard
from services.scrapers.remoteok import scan_remoteok
from services.scrapers.laborum import scan_laborum
from services.scrapers.firstjob import scan_firstjob
from services.scrapers.indeed import scan_indeed
from services.scrapers.trabajando import scan_trabajando
from services.scrapers.randstad import scan_randstad
from services.scrapers.bebee import scan_bebee

__all__ = [
    "scan_chiletrabajos", "scan_computrabajo",
    "scan_getonboard", "scan_remoteok",
    "scan_laborum", "scan_firstjob",
    "scan_indeed", "scan_trabajando",
    "scan_randstad",
    "scan_bebee",
]
