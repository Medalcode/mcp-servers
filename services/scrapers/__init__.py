from services.scrapers.chiletrabajos import scan_chiletrabajos
from services.scrapers.computrabajo import scan_computrabajo
from services.scrapers.getonboard import scan_getonboard
from services.scrapers.remoteok import scan_remoteok
from services.scrapers.laborum import scan_laborum
from services.scrapers.firstjob import scan_firstjob

__all__ = [
    "scan_chiletrabajos", "scan_computrabajo",
    "scan_getonboard", "scan_remoteok",
    "scan_laborum", "scan_firstjob",
]
