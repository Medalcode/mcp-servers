import sys
import os
import asyncio
import argparse

# Ensure we can import from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai_provider import parse_cv_with_ai
from database.repos.profiles import save_parsed_cv

async def main():
    parser = argparse.ArgumentParser(description="Ingest CV into Pathwise DB using AI")
    parser.add_argument("cv_path", help="Path to the CV file (PDF or TXT)")
    args = parser.parse_args()

    if not os.path.exists(args.cv_path):
        print(f"Error: File {args.cv_path} not found.")
        return

    text = ""
    if args.cv_path.lower().endswith(".pdf"):
        try:
            import pypdf
            print("Reading PDF with pypdf...")
            with open(args.cv_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        except ImportError:
            print("pypdf is not installed. Attempting to use pdftotext...")
            import subprocess
            try:
                result = subprocess.run(["pdftotext", args.cv_path, "-"], capture_output=True, text=True, check=True)
                text = result.stdout
            except Exception as e:
                print(f"Failed to read PDF. Please 'pip install pypdf' or install poppler-utils. Error: {e}")
                return
    else:
        with open(args.cv_path, "r", encoding="utf-8") as f:
            text = f.read()

    print("Sending CV to AI for structuring... (This may take a minute)")
    data = await parse_cv_with_ai(text)
    if "error" in data:
        print(f"Error parsing CV: {data['error']}")
        return
        
    print("\nCV parsed successfully! Extracted sections:")
    print(f"- Name: {data.get('personalInfo', {}).get('firstName', '')} {data.get('personalInfo', {}).get('lastName', '')}")
    print(f"- Experience: {len(data.get('experience', []))} entries")
    print(f"- Education: {len(data.get('education', []))} entries")
    print(f"- Skills: {len(data.get('skills', []))} entries")
    
    print("\nSaving to database as the default profile...")
    pid = save_parsed_cv(data, profile_name="Mi CV (AI)")
    print(f"Saved successfully as Profile ID: {pid}")

if __name__ == "__main__":
    asyncio.run(main())
