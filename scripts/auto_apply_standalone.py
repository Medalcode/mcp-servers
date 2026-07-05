import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

chromedriver_port = os.environ.get("CHROMEDRIVER_PORT", "38731")
driver = webdriver.Remote(
    command_executor=f"http://127.0.0.1:{chromedriver_port}",
    options=webdriver.ChromeOptions()
)
wait = WebDriverWait(driver, 10)

def click(by, value, timeout=10):
    try:
        el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
        driver.execute_script("arguments[0].scrollIntoView(true);", el)
        el.click()
        return True
    except Exception:
        return False

def fill(by, value, text, timeout=10):
    try:
        el = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
        driver.execute_script("arguments[0].scrollIntoView(true);", el)
        if el.tag_name == "select":
            Select(el).select_by_visible_text(text)
        else:
            el.clear()
            el.send_keys(text)
        return True
    except Exception:
        return False

def getonboard(url):
    print(f"\n=== GetOnBoard: {url} ===")
    driver.get(url)
    time.sleep(4)
    # Click "Apply now" link
    for sel in ["a[href$='/applications/new']", "a:has(svg)", "a[href*='/applications/new']"]:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                el.click()
                time.sleep(3)
                print(f"Clicked apply, now at: {driver.current_url}")
                break
        except Exception:
            continue
    print(f"  Final URL: {driver.current_url}")
    print(f"  Body: {driver.find_element(By.TAG_NAME, 'body').text[:300]}")

def firstjob(url):
    print(f"\n=== FirstJob: {url} ===")
    driver.get(url)
    time.sleep(5)
    print(f"  URL: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, 'body').text[:800]
    print(f"  Body: {body}")
    # Click "Postular"
    click(By.XPATH, "//*[contains(text(), 'Postular') or contains(text(), 'Apply')]")
    time.sleep(3)
    print(f"  After click: {driver.current_url}")

def successfactors(url):
    print(f"\n=== SuccessFactors: {url} ===")
    driver.get(url)
    time.sleep(5)
    print(f"  URL: {driver.current_url}")
    # Try to click Apply button
    for text in ["Apply Now", "Postular", "Apply", "Solicitar"]:
        if click(By.XPATH, f"//*[contains(text(), '{text}')]"):
            print(f"  Clicked '{text}'")
            time.sleep(3)
            break
    print(f"  After click: {driver.current_url}")
    body = driver.find_element(By.TAG_NAME, 'body').text[:500]
    print(f"  Body: {body[:300]}")

jobs = [
    ("getonboard", "Ejecutivo de Soporte Trainee - AgendaPro",
     "https://www.getonbrd.com/jobs/customer-support/ejecutivo-de-soporte-trainee-agendapro-santiago-b27f"),
    ("getonboard", "Analista de Automatización y Datos - BC Tecnología",
     "https://www.getonbrd.com/empleos/ingenieria-informatica/analista-de-automatizacion-y-datos-bc-tecnologia-santiago"),
    ("firstjob", "Práctica Profesional QA - Ripley",
     "https://firstjob.me/oferta/55131/practica-profesional-qa"),
    ("firstjob", "Práctica Profesional Gobierno de Datos - Ripley",
     "https://firstjob.me/oferta/55120/practica-profesional-gobierno-de-datos"),
    ("successfactors", "Fresh Graduates Chile - SONDA",
     "https://career5.successfactors.eu/career?career_company=sonda&career_job_req_id=6889&company=sonda&lang=en_US&job_location=chile&navBarLevel=JOB_SEARCH&selected_lang=en_US"),
    ("successfactors", "Internship Chile - SONDA",
     "https://career5.successfactors.eu/career?career_company=sonda&career_job_req_id=6897&company=sonda&lang=en_US&job_location=chile&navBarLevel=JOB_SEARCH&selected_lang=en_US"),
    ("successfactors", "Analista Funcional Mejora Sistemas Fresh Graduates - SONDA",
     "https://career5.successfactors.eu/career?career_company=sonda&career_job_req_id=6894&company=sonda&lang=en_US&job_location=chile&navBarLevel=JOB_SEARCH&selected_lang=en_US"),
]

for platform, title, url in jobs:
    try:
        if platform == "getonboard":
            getonboard(url)
        elif platform == "firstjob":
            firstjob(url)
        elif platform == "successfactors":
            successfactors(url)
    except Exception as e:
        print(f"  ERROR: {e}")

driver.quit()
