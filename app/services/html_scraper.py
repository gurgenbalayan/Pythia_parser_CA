import json
import random
import re
import shutil
import string
from typing import Dict
from selenium.webdriver import Keys
import seleniumwire.undetected_chromedriver.v2 as uc
import aiohttp
from utils.logger import setup_logger
import os
from fake_useragent import UserAgent
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common import WebDriverException, TimeoutException
from seleniumwire import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
load_dotenv()

STATE = os.getenv("STATE")
logger = setup_logger("scraper")

async def get_cookies_from_website(query: str) -> Dict[str, str]:
    cookies_dict = {}
    driver = None
    try:
        ua = UserAgent()
        user_agent = ua.random
        options = webdriver.ChromeOptions()
        script_dir = os.path.dirname(os.path.realpath(__file__))
        profile = os.path.join(script_dir, "profile")
        if not os.path.exists(profile):
            os.makedirs(profile)
        else:
            shutil.rmtree(profile)
        word = ''.join(random.choices(string.ascii_letters, k=10))
        profile_path = os.path.join(profile, word)
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument(f'--user-agent={user_agent}')
        options.add_argument('--lang=en-US')
        # options.add_argument("--headless=new")
        options.add_argument("--start-maximized")
        options.page_load_strategy = 'eager'
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
        options.add_argument("--force-webrtc-ip-handling-policy=default_public_interface_only")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-features=DnsOverHttps")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = uc.Chrome(options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                                    const getContext = HTMLCanvasElement.prototype.getContext;
                                    HTMLCanvasElement.prototype.getContext = function(type, attrs) {
                                        const ctx = getContext.apply(this, arguments);
                                        if (type === '2d') {
                                            const originalToDataURL = this.toDataURL;
                                            this.toDataURL = function() {
                                                return "data:image/png;base64,fake_canvas_fingerprint";
                                            };
                                        }
                                        return ctx;
                                    };
                                    """
        })
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                                Object.defineProperty(navigator, 'webdriver', {
                                  get: () => undefined
                                })
                              '''
        })
        try:
            driver.get("https://bizfileonline.sos.ca.gov/search/business")


            input_field = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.TAG_NAME, "input")))
            input_field.send_keys(query)
            input_field.send_keys(Keys.RETURN)

            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR,
                                                         "#root > div > div.content > div > main > div.table-wrapper > table > tbody")))
            for x in driver.requests:
                if x.host == "bizfileonline.sos.ca.gov" and x.method == "POST" and x.path == "/api/Records/businesssearch":
                    byte_str = x.response.body
                    decoded_content = brotli.decompress(byte_str)
                    decoded_string = decoded_content.decode('utf-8', errors='ignore')
                    json_data = json.loads(decoded_string)
            # driver.execute_script(f"window.location.href='{url}';")
            cookies_raw = driver.get_cookies()
            cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies_raw}
        except TimeoutException as e:
            logger.error(f"Page load error for load cookie: {e}")
        except WebDriverException as e:
            logger.error(f"WebDriver error: {e}")
    except Exception as e:
        logger.error(f"Ошибка при запуске Selenium: {e}")
    finally:
        if driver:
            driver.quit()
    return cookies_dict
async def fetch_company_details(url: str) -> dict:
    try:
        match = re.search(r"/business/([A-Z0-9]+)/", url)
        if match:
            id = match.group(1)
            url_search = "https://bizfileonline.sos.ca.gov/api/Records/businesssearch"
            payload = json.dumps({
                "SEARCH_VALUE": id,
                "STARTS_WITH_YN": True,
                "CRA_SEARCH_YN": False,
                "ACTIVE_ONLY_YN": False,
                "FILING_DATE": {
                    "start": None,
                    "end": None
                }
            })
            headers = {
                'Content-Type': 'application/json'
            }
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(url_search, data=payload) as response:
                    response.raise_for_status()
                    data = json.loads(await response.text())
                    result = await parse_html_name_agent(data)
                    record_num, id, name, agent = result["record_num"], result["id"], result["name"], result["agent"]
        else:
            logger.error(f"Error fetching data for query '{url}'")
            return []
        new_url = re.sub(r'(?<=business/)\d+(?=/)', id, url)
        async with aiohttp.ClientSession() as session:
            async with session.get(new_url) as response:
                response.raise_for_status()
                data = json.loads(await response.text())
                return await parse_html_details(data, record_num, id, name, agent)
    except Exception as e:
        logger.error(f"Error fetching data for query '{url}': {e}")
        return []
async def fetch_company_data(query: str) -> list[dict]:
    cookies = await get_cookies_from_website(query)
    url = "https://bizfileonline.sos.ca.gov/api/Records/businesssearch"

    payload = json.dumps({
        "SEARCH_VALUE": query,
        "SEARCH_FILTER_TYPE_ID": "0",
        "SEARCH_TYPE_ID": "1",
        "FILING_TYPE_ID": "",
        "STATUS_ID": "",
        "FILING_DATE": {
            "start": None,
            "end": None
        },
        "CORPORATION_BANKRUPTCY_YN": False,
        "CORPORATION_LEGAL_PROCEEDINGS_YN": False,
        "OFFICER_OBJECT": {
            "FIRST_NAME": "",
            "MIDDLE_NAME": "",
            "LAST_NAME": ""
        },
        "NUMBER_OF_FEMALE_DIRECTORS": "99",
        "NUMBER_OF_UNDERREPRESENTED_DIRECTORS": "99",
        "COMPENSATION_FROM": "",
        "COMPENSATION_TO": "",
        "SHARES_YN": False,
        "OPTIONS_YN": False,
        "BANKRUPTCY_YN": False,
        "FRAUD_YN": False,
        "LOANS_YN": False,
        "AUDITOR_NAME": ""
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'undefined'
    }
    try:
        async with aiohttp.ClientSession(cookies=cookies, headers=headers) as session:
            async with session.post(url, data=payload) as response:
                response.raise_for_status()
                test = await response.text()
                data = json.loads(test)
                return await parse_html_search(data)
    except Exception as e:
        logger.error(f"Error fetching data for query '{query}': {e}")
        return []

async def parse_html_search(data: dict) -> list[dict]:
    results = []
    for entity_id, data_row in data["rows"].items():
        entity_name = data_row.get("TITLE", [""])[0]  # берём первую строку из TITLE
        status = data_row.get("STATUS", "")
        id = data_row.get("RECORD_NUM", "").lstrip("0")
        results.append({
                "state": STATE,
                "name": entity_name,
                "status": status,
                "id": entity_id,
                "url": f"https://bizfileonline.sos.ca.gov/api/FilingDetail/business/{id}/false"
            })
    return results

async def parse_html_name_agent(data: dict) -> dict:
    for entity_id, data_row in data["rows"].items():
        entity_name = data_row.get("TITLE", [""])[0]  # берём первую строку из TITLE
        agent = data_row.get("AGENT", "")
        record_num = data_row.get("RECORD_NUM", "")
        return {
            "record_num": record_num,
            "id": entity_id,
            "name": entity_name,
            "agent": agent
        }


async def parse_html_details(data: dict, record_num: str, id: str, name: str, agent: str) -> dict:
    async def fetch_documents(record_num: str) -> list[dict]:
        url = f"https://bizfileonline.sos.ca.gov/api/History/business/{record_num}"
        headers = {
            'Content-Type': 'application/json'
        }
        results = []
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = json.loads(await response.text())
                    base_url = "https://bizfileonline.sos.ca.gov"
                    for amendment in data["AMENDMENT_LIST"]:
                        try:
                            download_link = base_url + amendment["DOWNLOAD_LINK"]
                            file_name = amendment["AMENDMENT_TYPE"]
                            file_date = amendment["AMENDMENT_DATE"]
                            results.append({
                                "name": file_name,
                                "date": file_date,
                                "link": download_link,
                            })
                        except Exception as e:
                            continue
                    return results
        except Exception as e:
            logger.error(f"Error fetching data for record_num '{record_num}': {e}")
            return []


    detail_map = {item["LABEL"]: item["VALUE"] for item in data.get("DRAWER_DETAIL_LIST", [])}
    mailing_address = detail_map.get("Mailing Address") or ""
    principal_address = detail_map.get("Principal Address") or ""
    document_images = await fetch_documents(record_num)
    status = detail_map.get("Status")
    date_registered = detail_map.get("Initial Filing Date")
    entity_type = detail_map.get("Filing Type")
    return {
        "state": STATE,
        "name": name,
        "status": status.strip() if status else None,
        "registration_number": id,
        "date_registered": date_registered.strip() if date_registered else None,
        "entity_type": entity_type.strip() if entity_type else None,
        "agent_name": agent,
        "principal_address": principal_address.strip() if principal_address else None,
        "mailing_address": mailing_address.strip() if mailing_address else None,
        "document_images": document_images
    }