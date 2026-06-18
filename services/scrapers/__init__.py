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

from services.scrapers.ibm import scan_ibm
from services.scrapers.microsoft import scan_microsoft
from services.scrapers.nestle import scan_nestle
from services.scrapers.cocacola import scan_cocacola
from services.scrapers.pepsico import scan_pepsico
from services.scrapers.sap import scan_sap
from services.scrapers.cencosud import scan_cencosud
from services.scrapers.falabella import scan_falabella
from services.scrapers.latam import scan_latam
from services.scrapers.entel import scan_entel
from services.scrapers.bci import scan_bci

__all__ = [
    "scan_chiletrabajos", "scan_computrabajo",
    "scan_getonboard", "scan_remoteok",
    "scan_laborum", "scan_firstjob",
    "scan_indeed", "scan_trabajando",
    "scan_randstad", "scan_bebee", "scan_sonda",
    "scan_bhp", "scan_codelco",
    "scan_freeport", "scan_teck",
    "scan_lundin", "scan_glencore",
    "scan_ibm", "scan_microsoft", "scan_nestle",
    "scan_cocacola", "scan_pepsico", "scan_sap",
    "scan_cencosud", "scan_falabella", "scan_latam",
    "scan_entel", "scan_bci"
]
