# SearchIQS Ashford, CT — Land Records Scraper
Python-based scraper for the SearchIQS Ashford, CT website.

# Sample output:
https://docs.google.com/spreadsheets/d/1uFZiRBIMGGnJxRCmIoRDrPD7lVor8PpKBaFy6qFaU7M/edit?gid=0#gid=0

Exported columns: `Party 1`, `Party 2`, `Type`, `Book-Page`, `Date`,
`Description`, `Additional Description`, `Related` 

## Setup

1. **Python + dependencies** :
   ```bash
   pip install -r requirements.txt
   ```
   (`curl_cffi`, `beautifulsoup4`, `gspread`, `google-auth`)

2. **VPN** — connect to a US server (ProtonVPN works); 
    pick one server and stay on it for both the cookie step below and the run.

3. **Clearance cookie** — in your browser, open
   <https://www.searchiqs.com/CTASH/> and check on "Verify you are a human",
   and after that page opens go on DevTools → Application/Storage → Cookies → copy the `cf_clearance`
   value and that browser's User-Agent string.

4. **`.env`** — create from the template below and fill in:
   ```
   CF_CLEARANCE=<paste cf_clearance from step 3>
   CF_USER_AGENT=<paste the same browser's User-Agent>
   SHEET_URL=<URL of the target Google Sheet>
   ```

5. **Google Sheet + service account** —
   - Create service account through [Google Cloud Console](https://console.cloud.google.com)
     and download its JSON key as `creds.json` in this folder
   - Create a spreadsheet, share it with the service account's email
     (`...@....iam.gserviceaccount.com`) as **Editor**
   - Set general access to **"anyone with the link → Viewer"** and put its URL
     in `.env` as `SHEET_URL` as in step 4

## Run

```bash
python main.py
```

## Expected console output :

```
Searching for past 80 days, from 24/07/2026 to 12/10/2026...
page 1: 100 records 
page 2: 44 records
TOTAL: 144 records
Exported 144 records -> <SHEET_URL>
```

## Files

| File | Purpose |
|---|---|
| `main.py` | Full pipeline (login → search → paginate → Sheets export) |
| `formCheck.py` | Debug helper: dumps a saved HTML page's forms, fields, postback targets and tables |
| `requirements.txt` | Python dependencies |
| `creds.json` | Service-account key (**do not commit/share**) |
| `.env` | Cookie, UA, sheet URL (**do not commit/share**) |
