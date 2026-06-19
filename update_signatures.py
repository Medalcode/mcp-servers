import glob
import re

files = glob.glob('/run/media/medalcode/Interno_Sec/Github/mcp-servers/services/scrapers/*.py')
for f in files:
    with open(f, 'r') as file:
        content = file.read()
    
    # Matches: async def scan_X(query: str, location: str = "") -> list:
    # and variations
    new_content = re.sub(
        r'async def scan_([a-zA-Z0-9_]+)\(query:\s*str,\s*location:\s*str\s*=\s*"([^"]*)"\)\s*->\s*list:',
        r'async def scan_\1(query: str, location: str = "\2", filters: dict = None) -> list:',
        content
    )
    
    # Also for Sonda which might have location: str = "" instead
    new_content = re.sub(
        r'async def scan_sonda\(query:\s*str,\s*location:\s*str\s*=\s*""\)\s*->\s*list:',
        r'async def scan_sonda(query: str, location: str = "", filters: dict = None) -> list:',
        new_content
    )
    
    # Also GetOnBoard which is scan_getonboard(query: str, location: str = "Chile") -> list:
    new_content = re.sub(
        r'async def scan_([a-zA-Z0-9_]+)\(query:\s*str,\s*location:\s*str\s*=\s*"Chile"\)\s*->\s*list:',
        r'async def scan_\1(query: str, location: str = "Chile", filters: dict = None) -> list:',
        new_content
    )
    
    if new_content != content:
        with open(f, 'w') as file:
            file.write(new_content)
        print(f"Updated {f}")
