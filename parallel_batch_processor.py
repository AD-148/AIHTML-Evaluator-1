import pandas as pd
import requests
import json
import uuid
import concurrent.futures
import os
import logging
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Worker-%(threadName)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- Configuration ---
BASE_URL = "https://html-ai-template.moestaging.com/api/v1/bff/response/stream"

# Strict Instruction
BYPASS_INSTRUCTION = " Do not ask for clarification. If details are missing, make a reasonable assumption based on the context and proceed. If multiple valid options exist, choose the most common one. Your goal is to provide a final answer in the first response."

# Headers (Copied from backend/moengage_api.py)
HEADERS = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "moetraceid": "d39639d2-a4c3-4da8-8b62-185294eda567",
    "origin": "https://html-ai-template.moestaging.com",
    "page": "inapp/edit/69439a204e66b370a00fadaa",
    "priority": "u=1, i",
    "refreshtoken": "0d403795-1b35-4e7f-a919-becae42ef23f",
    "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
}

# Auth Tokens (Fallback for script usage)
AUTH_TOKEN = os.environ.get("MOENGAGE_BEARER_TOKEN", "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE1NzI1MTI0NTciLCJ0eXAiOiJKV1QifQ.eyJhcHAiOnsiYXBwX2tleSI6IkNNNEQxTFpOMklNSk5CWTlVTFhBVTczRCIsImRiX25hbWUiOiJ6YWluX2luYXBwIiwiZGlzcGxheV9uYW1lIjoiemFpbl9pbmFwcCIsImVudmlyb25tZW50IjoibGl2ZSIsImlkIjoiNjM5ODUyZWViMGVjOWFiMzhhNzkyMTg5In0sImV4cCI6MTc3MTMwMjc0NiwiaWF0IjoxNzY2MDQ2NzQ2LCJpc3MiOiJhcHAubW9lbmdhZ2UuY29tIiwibmJmIjoxNzY2MDQ2NzQ2LCJyb2xlIjoiQWRtaW4iLCJ1c2VyIjp7IjJGQSI6dHJ1ZSwiZW1haWwiOiJhcmlqaXQuZGFzQG1vZW5nYWdlLmNvbSIsImlkIjoiNjNkY2VmODc4MGU5MzdiODljMTRjYjM3IiwibG9naW5fdHlwZSI6IlNURCJ9fQ.cCfP8y73ClnomYmWXyzr1CD3K74DebO5zHWwCMitzxxcdJ73HZTDepkz-5ufdRwnx10YchsrlqTx2aktESzi_zSq3VptSJr6s9WZVS8zs_43QcPSB5E0B6a6Ijo6qdwdnA9fyafdgs7LWw_XaJt9Fu4Mb2lQYjeV1wZb5kY8Vs76f7rIr81Bpaoa70-_Z3rfSteD3_N3gicJ4eKZVqmxYrX-GbIiGuN6kNthm-Wz9_cbbuIde4lhALrzje1y9AKIJZxCRYi5d8FBpnnAj4YWg6IB6mwG3rIvhgM7O-_Zm27IiDGAlEAxYAvYB7tsOVRZusm_a5SEqqJlChmuyidaPw")
COOKIES = os.environ.get("MOENGAGE_COOKIES", "moe_c_s=1; moe_uuid=56baa3f7-285d-49c1-b67e-5482e2755748; moe_u_d=HcfBCoAgDADQf9m5XdSl9jOiboNACDJP0b8nHt8LPV2N4dDcumzAKTPL9HOPxXFOgK1UPZuIFIKgC5Ew-lzQOxYtVIzuFr4f; moe_s_n=RcoxDsIwDIXhu3hOJLs1dtKrIGTJppUQAoZ0Q9ydpEvH97_vC82esEBwZfd6zzEVyYyI2TenvLKGbkIY4pA6brbDQioyz0SsRWXU11ELYoKwh-1jXm_jWU8_1e7rJcHbPtZ65d8f")

def process_row(index, prompt):
    """
    Processes a single row: generates HTML via streaming API.
    Returns: (index, html_content)
    """
    if not prompt or pd.isna(prompt):
        return index, "SKIPPED_EMPTY"

    full_prompt = str(prompt) + BYPASS_INSTRUCTION
    
    # 1. Generate Dynamic Session ID
    session_id = str(uuid.uuid4())
    
    # 2. Construct Query Params
    params = {
        "user_id": "arijit.das@moengage.com",
        "session_id": session_id,
        "agent_id": "inapp-html-ai-v1"
    }
    
    # Construct Full URL
    url_parts = list(urlparse(BASE_URL))
    query = dict(parse_qs(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query, doseq=True)
    full_url = urlunparse(url_parts)
    
    # 3. Prepare Payload & Headers
    payload = {
        "payload": {
            "type": "user",
            "text": full_prompt
        }
    }
    
    request_headers = HEADERS.copy()
    request_headers["authorization"] = f"Bearer {AUTH_TOKEN}"
    request_headers["cookie"] = COOKIES

    final_html = ""
    
    try:
        logger.info(f"Row {index}: Starting Request (Session: {session_id})...")
        
        # 4. Execute Streaming Request
        with requests.post(full_url, json=payload, headers=request_headers, stream=True, timeout=900) as response:
            if response.status_code != 200:
                logger.error(f"Row {index}: API Error {response.status_code}")
                return index, f"ERROR_{response.status_code}"

            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    # Stream format: "data: {...}"
                    if decoded_line.startswith("data:"):
                        decoded_line = decoded_line[5:].strip()
                    
                    try:
                        json_data = json.loads(decoded_line)
                        # Path: preview-payload -> data -> html
                        html_chunk = json_data.get("preview-payload", {}).get("data", {}).get("html")
                        if html_chunk:
                            final_html = html_chunk
                    except json.JSONDecodeError:
                        continue
        
        if final_html:
            logger.info(f"Row {index}: Success ({len(final_html)} chars)")
            return index, final_html
        else:
            logger.warning(f"Row {index}: Completed but NO HTML found.")
            return index, "NO_HTML_FOUND"

    except Exception as e:
        logger.error(f"Row {index}: Exception: {e}")
        return index, f"EXCEPTION: {str(e)}"

def main():
    # Fallback to CSV to avoid openpyxl dependency issues
    INPUT_FILE = "prompts.csv"
    OUTPUT_FILE = "output_parallel.csv"
    MAX_WORKERS = 5
    
    if not os.path.exists(INPUT_FILE):
        # Convert Excel to CSV if exists, else error
        if os.path.exists("prompts.xlsx"):
             logger.info("Converting prompts.xlsx to prompts.csv...")
             try:
                 pd.read_excel("prompts.xlsx").to_csv(INPUT_FILE, index=False)
             except Exception as e:
                 logger.error(f"Failed to convert Excel: {e}")
                 return
        else:
             logger.error(f"Input file '{INPUT_FILE}' (or .xlsx) not found.")
             return

    logger.info(f"Reading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)
    
    if "Prompt" not in df.columns:
        logger.error("Column 'Prompt' missing in CSV.")
        return

    # Initialize Output Column
    df["Generated HTML"] = ""
    
    # Prepare Tasks
    rows_to_process = []
    for index, row in df.iterrows():
        rows_to_process.append((index, row["Prompt"]))
    
    logger.info(f"Starting parallel processing for {len(rows_to_process)} rows with {MAX_WORKERS} workers...")
    
    results = {}
    
    # Execute in Parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(process_row, idx, prompt): idx 
            for idx, prompt in rows_to_process
        }
        
        for future in concurrent.futures.as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                processed_idx, html_output = future.result()
                results[processed_idx] = html_output
            except Exception as e:
                logger.error(f"Row {idx} generated an exception: {e}")
                results[idx] = f"THREAD_EXCEPTION: {e}"
    
    # Consolidate Results in Order
    logger.info("Consolidating results...")
    for idx, html_content in results.items():
        df.at[idx, "Generated HTML"] = html_content

    # Save Output
    logger.info(f"Saving to {OUTPUT_FILE}...")
    df.to_csv(OUTPUT_FILE, index=False)
    logger.info("Done!")

if __name__ == "__main__":
    main()
