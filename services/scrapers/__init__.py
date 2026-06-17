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
from services.scrapers.sonda import scan_sonda
from services.scrapers.bhp import scan_bhp
from services.scrapers.codelco import scan_codelco
from services.scrapers.freeport import scan_freeport
from services.scrapers.teck import scan_teck
from services.scrapers.lundin import scan_lundin
from services.scrapers.glencore import scan_glencore

__all__ = [
    "scan_chiletrabajos", "scan_computrabajo",
    "scan_getonboard", "scan_remoteok",
    "scan_laborum", "scan_firstjob",
    "scan_indeed", "scan_trabajando",
    "scan_randstad", "scan_bebee", "scan_sonda",
    "scan_bhp", "scan_codelco",
    "scan_freeport", "scan_teck",
    "scan_lundin", "scan_glencore",
]
