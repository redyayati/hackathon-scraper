from curl_cffi import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import date , timedelta
import gspread , os
from google.oauth2.service_account import Credentials

BASE_URL = "https://www.searchiqs.com/CTASH/"

NUMBER_OF_DAYS = 80

FIELDS = ["Party 1", "Party 2", "Type", "Book-Page", "Date",
          "Description", "Additional Description", "Related"]
request_timeout = 10

ENV_FILE = ".env"

def load_env(path=ENV_FILE):
    env = {}
    if not os.path.exists(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

ENV = load_env()
CLEARANCE_COOKIE = ENV.get("CF_CLEARANCE", "")
USER_AGENT = ENV.get("CF_USER_AGENT", "")
SHEET_URL = ENV.get("SHEET_URL", "")

def new_session(): 
    s = requests.Session(impersonate="chrome124")
    s.headers["User-Agent"] = USER_AGENT
    s.cookies.set('cf_clearance', CLEARANCE_COOKIE)
    return s    

def guest_login(session): 
    login = session.get(BASE_URL, timeout = request_timeout)
    if "Just a moment" in login.text or login.status_code != 200:
        raise SystemExit("clearance_cookie expired — refresh it from the browser")
    guest = postback(session , login.text , login.url, event_target="btnGuestLogin")
    return guest

def postback(session, page_html , page_url , fields = {} , event_target = None): 
    soup = BeautifulSoup(page_html, "html.parser")
    target_url = urljoin(page_url , soup.find("form").get("action"))
    payload = {}
    for tag in soup.find_all("input", {"type" : "hidden"}) : 
        if tag.get("name") : 
            payload[tag["name"]] = tag.get("value", "")
    payload.update(fields)
    if event_target : 
        payload["__EVENTTARGET"] = event_target
        payload["__EVENTARGUMENT"] = ""
    return session.post(target_url , data=payload , headers={"Referer" : page_url} , timeout=request_timeout)

def parse_records(page_html): 
    soup = BeautifulSoup(page_html , "html.parser")
    grid = soup.find(id="ContentPlaceHolder1_grdResults")
    if grid is None : return []
    rows = grid.find_all("tr")
    pos = {name: i for i, name in enumerate(
        c.get_text(strip=True) for c in rows[0].find_all(["th", "td"]))}
    records = []
    for tr in rows[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        # if len(cells) >= 12 and cells[3]:
        records.append({f: cells[pos[f]] for f in FIELDS})
    return records

def total_pages(page_html):
    soup = BeautifulSoup(page_html, "html.parser")
    ddl = soup.find(id="ContentPlaceHolder1_ddlGoToPage1")
    return len(ddl.find_all("option")) if ddl else 1

def run_search(session , search_page): 
    today = date.today()
    from_day = today - timedelta(days=NUMBER_OF_DAYS)
    if NUMBER_OF_DAYS > 90:
        raise SystemExit("limit the date range to a maximum of 90 days.")
    print(f"Searching for past {NUMBER_OF_DAYS} days, from {from_day:%d/%m/%Y} to {today:%d/%m/%Y}...")
    
    group_page = postback(session, search_page.text , search_page.url, 
                          fields={"ctl00$ContentPlaceHolder1$cboDocGroup" : "LR"} , 
                          event_target="ctl00$ContentPlaceHolder1$cboDocGroup")
    filledFields = {
        "ctl00$ContentPlaceHolder1$cboDocGroup" : "LR",
        "ctl00$ContentPlaceHolder1$txtFromDate" : from_day.strftime("%m/%d/%Y") , 
        "ctl00$ContentPlaceHolder1$txtThruDate" :  today.strftime("%m/%d/%Y") , 
        "ctl00$ContentPlaceHolder1$cmdSearch" : "Search"
    }

    results = postback(session, group_page.text , group_page.url , fields=filledFields)

    return results


def scrap_all_pages(session , results_page): 
    records = parse_records(results_page.text)
    if not records:
        raise SystemExit("No records parsed — keeping existing sheet untouched")
    resp, page = results_page, 1
    print(f"page {page} : {len(records)} records")
    num_pages = total_pages(resp.text)    
    for page in range(2, num_pages + 1) : 
        resp = postback(session, resp.text, resp.url,
                        event_target="ctl00$ContentPlaceHolder1$lbNext1")
        new = parse_records(resp.text)
        if not new:
            raise SystemExit(f"Page {page} returned no records — "
                                "aborting before a partial export")
        records.extend(new)
        print(f"page {page} : {len(new)} records")
    return records

def export_to_sheet(records): 
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("creds.json" , scopes=scopes)
    client = gspread.authorize(creds)
    # SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFZiRBIMGGnJxRCmIoRDrPD7lVor8PpKBaFy6qFaU7M/edit?gid=0#gid=0"
    sheet = client.open_by_url(SHEET_URL)
    ws = sheet.sheet1

    ws.clear()
    ws.append_rows([FIELDS])
    ws.append_rows([[r[f] for f in FIELDS] for r in records])
    print(f"Exported {len(records)} records -> {SHEET_URL}")


def main():
    session = new_session()
    search_page = guest_login(session)
    result_page = run_search(session , search_page)
    records = scrap_all_pages(session , result_page)
    print(f"TOTAL: {len(records)} records")

    export_to_sheet(records)

if __name__ == "__main__":
    main()
