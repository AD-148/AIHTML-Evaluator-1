import requests
import json
import os
import logging

logger = logging.getLogger(__name__)

# Strict Instruction to prevent conversational callbacks
BYPASS_INSTRUCTION = " Do not ask for clarification. If details are missing, make a reasonable assumption based on the context and proceed. If multiple valid options exist, choose the most common one. Your goal is to provide a final answer in the first response."

# Configuration (Should be in .env, but defaults provided for immediate usage)
API_URL = "https://html-ai-template.moestaging.com/api/v1/bff/response/stream?user_id=arijit.das@moengage.com&session_id=a56958c9-2828-4ad1-8ef3-1e72806ef628&agent_id=inapp-html-ai-v1"

# Headers from User CURL
# Note: In a real prod env, these should be rotated and loaded from secrets.
HEADERS = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    # "authorization": "Bearer ...", # Loaded from env or fallback
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

import uuid
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def generate_html_from_stream(prompt: str) -> str:
    """
    Calls the MoEngage Streaming API with the prompt + strict instruction.
    Parses the JSON stream to find 'preview-payload.data.html'.
    Returns the final HTML string found.
    """
    full_prompt = str(prompt) + BYPASS_INSTRUCTION
    
    # Load sensitive keys from Env or Hardcoded Fallback (for demo)
    auth_token = os.environ.get("MOENGAGE_BEARER_TOKEN", "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE1NzI1MTI0NTciLCJ0eXAiOiJKV1QifQ.eyJhcHAiOnsiYXBwX2tleSI6IkNNNEQxTFpOMklNSk5CWTlVTFhBVTczRCIsImRiX25hbWUiOiJ6YWluX2luYXBwIiwiZGlzcGxheV9uYW1lIjoiemFpbl9pbmFwcCIsImVudmlyb25tZW50IjoibGl2ZSIsImlkIjoiNjM5ODUyZWViMGVjOWFiMzhhNzkyMTg5In0sImV4cCI6MTc3MTMwMjc0NiwiaWF0IjoxNzY2MDQ2NzQ2LCJpc3MiOiJhcHAubW9lbmdhZ2UuY29tIiwibmJmIjoxNzY2MDQ2NzQ2LCJyb2xlIjoiQWRtaW4iLCJ1c2VyIjp7IjJGQSI6dHJ1ZSwiZW1haWwiOiJhcmlqaXQuZGFzQG1vZW5nYWdlLmNvbSIsImlkIjoiNjNkY2VmODc4MGU5MzdiODljMTRjYjM3IiwibG9naW5fdHlwZSI6IlNURCJ9fQ.cCfP8y73ClnomYmWXyzr1CD3K74DebO5zHWwCMitzxxcdJ73HZTDepkz-5ufdRwnx10YchsrlqTx2aktESzi_zSq3VptSJr6s9WZVS8zs_43QcPSB5E0B6a6Ijo6qdwdnA9fyafdgs7LWw_XaJt9Fu4Mb2lQYjeV1wZb5kY8Vs76f7rIr81Bpaoa70-_Z3rfSteD3_N3gicJ4eKZVqmxYrX-GbIiGuN6kNthm-Wz9_cbbuIde4lhALrzje1y9AKIJZxCRYi5d8FBpnnAj4YWg6IB6mwG3rIvhgM7O-_Zm27IiDGAlEAxYAvYB7tsOVRZusm_a5SEqqJlChmuyidaPw")
    cookies_header = os.environ.get("MOENGAGE_COOKIES", "moe_c_s=1; moe_uuid=56baa3f7-285d-49c1-b67e-5482e2755748; moe_u_d=HcfBCoAgDADQf9m5XdSl9jOiboNACDJP0b8nHt8LPV2N4dDcumzAKTPL9HOPxXFOgK1UPZuIFIKgC5Ew-lzQOxYtVIzuFr4f; moe_s_n=RcoxDsIwDIXhu3hOJLs1dtKrIGTJppUQAoZ0Q9ydpEvH97_vC82esEBwZfd6zzEVyYyI2TenvLKGbkIY4pA6brbDQioyz0SsRWXU11ELYoKwh-1jXm_jWU8_1e7rJcHbPtZ65d8f")
    # Session ID must be valid and pre-existing
    session_id = os.environ.get("MOENGAGE_SESSION_ID", "a56958c9-2828-4ad1-8ef3-1e72806ef628")
    
    # Inject Session ID into URL
    url_parts = list(urlparse(API_URL))
    query = dict(parse_qs(url_parts[4]))
    query['session_id'] = session_id
    url_parts[4] = urlencode(query, doseq=True)
    dynamic_url = urlunparse(url_parts)
    
    payload = {
        "payload": {
            "type": "user",
            "text": full_prompt
        }
    }
    
    # Combine Headers
    request_headers = HEADERS.copy()
    request_headers["authorization"] = f"Bearer {auth_token}"
    
    # Parse Cookie String to Dict for robust Request handling
    cookie_dict = {}
    if cookies_header:
        try:
            for item in cookies_header.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookie_dict[k] = v
        except Exception:
            logger.warning("Failed to parse cookie string, using raw header fallback.")
            request_headers["cookie"] = cookies_header

    final_html = ""
    
    try:
        masked_token = auth_token[:10] + "..." if auth_token else "NONE"
        logger.info(f"API Call | Session: {session_id} | Token: {masked_token}")
        logger.info(f"Payload Preview: {str(payload)[:200]}...")
        
        # Timeout increased to 900s (15 mins) as generation can take ~4 mins
        # Use 'cookies' param if parsed, otherwise fallback to header is already handled above (but we remove it if dict exists to avoid dup)
        if cookie_dict:
             response = requests.post(dynamic_url, json=payload, headers=request_headers, cookies=cookie_dict, stream=True, timeout=900)
        else:
             response = requests.post(dynamic_url, json=payload, headers=request_headers, stream=True, timeout=900)
             
        with response:
            if response.status_code != 200:
                logger.error(f"MoEngage API Error {response.status_code}: {response.text[:200]}")
                return ""
                
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    # Log snippet if it's the first line or looks like a valid response starting
                    # but since it's a stream, let's wait until failure to log.
                    # We will store the LAST line seen for debug.
                    last_seen_line = decoded_line 
                    
                    try:
                        # Extract JSON data
                        if decoded_line.startswith("data:"):
                            decoded_line = decoded_line[5:].strip()
                        
                        json_data = json.loads(decoded_line)
                        
                        html_chunk = json_data.get("preview-payload", {}).get("data", {}).get("html")
                        
                        if html_chunk:
                            final_html = html_chunk
                            
                    except json.JSONDecodeError:
                        continue
                        
        if final_html:
            logger.info("Successfully extracted HTML from stream.")
            return final_html
        else:
            logger.warning("Stream finished but no HTML found.")
            # Log the last seen line to determine if it was empty or error JSON
            if 'last_seen_line' in locals():
                 logger.info(f"Last Stream Line: {last_seen_line[:500]}")
            else:
                 logger.info("Stream was empty (No lines yielded).")
            return ""
            
    except Exception as e:
        logger.error(f"Stream Request Failed: {e}", exc_info=True)
        return ""
