import requests
import json
import os
import logging

logger = logging.getLogger(__name__)

# Strict Instruction to prevent conversational callbacks
BYPASS_INSTRUCTION = " Do not ask for clarification. If details are missing, make a reasonable assumption based on the context and proceed. If multiple valid options exist, choose the most common one. Your goal is to provide a final answer in the first response."

# Configuration (Should be in .env, but defaults provided for immediate usage)
# Configuration (Should be in .env, but defaults provided for immediate usage)
API_BASE = "https://html-ai-template.moestaging.com/api/v1/bff"
API_URL = f"{API_BASE}/response/stream?user_id=sweta.agarwal@moengage.com&session_id={{}}&agent_id=inapp-html-ai-v1"
SESSION_URL = f"{API_BASE}/sessions"

# Headers from User CURL
# Note: In a real prod env, these should be rotated and loaded from secrets.
HEADERS = {
    "accept": "application/json",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "content-type": "application/json",
    # "authorization": "Bearer ...", # Loaded from env or fallback
    "moetraceid": "12d514c2-8c7a-4834-8701-299cfe141182",
    "origin": "https://html-ai-template.moestaging.com",
    "page": "inapp/create/",
    "priority": "u=1, i",
    "refreshtoken": "0e53c5e6-57c1-4522-85c2-dcff3946d41b",
    "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
}

import uuid
import time
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def get_common_headers(auth_token):
    req_headers = HEADERS.copy()
    req_headers["authorization"] = f"Bearer {auth_token}"
    return req_headers

def get_cookies_dict():
    cookies_header = os.environ.get("MOENGAGE_COOKIES", "moe_c_s=1; moe_uuid=df642ebc-c7cd-47d4-8497-c0557dfe9f73; moe_u_d=HcdBCoAgEAXQu8y6gZzEssuIMX8gEILMVXT3xOV7qaarKO2WS8VEmrIqup-7Dbazg2SGAC6yEwH7RT1nOwLLFiNWCwYP-n4; moe_s_n=RcpBDoQgDIXhu3QtSUHbKleZTBoESSYTdYE7490FNy7f_74Tiv7Bw0g25RzYpGCtGSY3m9DjbGJORCJDWKKDruKiB3grzITkeGLqW12fOiJ2EPWnR5ufb3uW1wtWL5VsumsBT9cN")
    cookie_dict = {}
    if cookies_header:
        try:
            for item in cookies_header.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookie_dict[k] = v
        except Exception:
            logger.warning("Failed to parse cookie string, using raw header fallback.")
    return cookie_dict

def create_new_session() -> str:
    """
    Creates a new session via the /sessions endpoint.
    Returns the session_id string.
    """
    auth_token = os.environ.get("MOENGAGE_BEARER_TOKEN", "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE1NzI1MTI0NTciLCJ0eXAiOiJKV1QifQ.eyJhcHAiOnsiYXBwX2tleSI6IkNNNEQxTFpOMklNSk5CWTlVTFhBVTczRCIsImRiX25hbWUiOiJ6YWluX2luYXBwIiwiZGlzcGxheV9uYW1lIjoiemFpbl9pbmFwcCIsImVudmlyb25tZW50IjoibGl2ZSIsImlkIjoiNjM5ODUyZWViMGVjOWFiMzhhNzkyMTg5In0sImV4cCI6MTc3MTczMDIzOSwiaWF0IjoxNzY2NDc0MjM5LCJpc3MiOiJhcHAubW9lbmdhZ2UuY29tIiwibmJmIjoxNzY2NDc0MjM5LCJyb2xlIjoiQWRtaW4iLCJ1c2VyIjp7IjJGQSI6dHJ1ZSwiZW1haWwiOiJzd2V0YS5hZ2Fyd2FsQG1vZW5nYWdlLmNvbSIsImlkIjoiNjIxZGE5ZDlhMGRmOThmNDkwMzIyYjgzIiwibG9naW5fdHlwZSI6IlNURCJ9fQ.fT5PL9PSZcT17XS5YC5Cky5n9W6-KFaNiKGSlq3Fglag8X5UiUEg4egRYIhf4YoZ6KxiGC-ppxYrvhrV8vE0XKmBESLLbqvoPtJ_hO7iXdStlnmTdpW3cKY4cyZmT3tkfFqLoXJX7srFDgE-w1z-ytITuchcitYUyCVw-FRM5kCh7KSJihBP0HzBw_P82i9iJi-3t0OxIRilWc36FmMMVasYtz2_tM00DU9qNGMOmq6BUAg-OtHia5HiSq14j1xylH0rof4OOP4zHf1LVIf7cOj5htUQooucrtOJQUPfRwFWrCEJ_zFjOfg1fUJwzy9c05xv44tzeuQatU9HL1Li6g")
    
    headers = get_common_headers(auth_token)
    cookie_dict = get_cookies_dict()
    
    # Payload for session creation (from CURL)
    payload = {"user_id": "sweta.agarwal@moengage.com", "agent_id": "inapp-html-ai-v1"}
    
    try:
        logger.info("Creating new session...")
        resp = requests.post(SESSION_URL, json=payload, headers=headers, cookies=cookie_dict, timeout=30)
        resp.raise_for_status()
        
        data = resp.json()
        # Assuming response structure based on typical API, if not we will debug.
        # Usually returns { "session_id": "..." } or similar
        # Based on prev code, we might need to inspect 'data'
        # If API returns straight JSON with session_id
        session_id = data.get("session_id")
        
        # If nested: data.get("data", {}).get("session_id")
        if not session_id:
             session_id = data.get("data", {}).get("session_id")
             
        if not session_id:
            logger.error(f"Could not extract session_id from {data}")
            raise ValueError("No session_id in response")
            
        logger.info(f"New Session Created: {session_id}")
        return session_id
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        # Fallback to a hardcoded one if session creation fails strictly? 
        # Or better to fail early.
        # We will return None to signal failure
        return None

def generate_html_from_stream(prompt: str, session_id: str = None) -> tuple[str, str]:
    """
    Calls the MoEngage Streaming API with the prompt.
    Requires a valid session_id.
    """
    full_prompt = str(prompt) + BYPASS_INSTRUCTION
    
    auth_token = os.environ.get("MOENGAGE_BEARER_TOKEN", "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE1NzI1MTI0NTciLCJ0eXAiOiJKV1QifQ.eyJhcHAiOnsiYXBwX2tleSI6IkNNNEQxTFpOMklNSk5CWTlVTFhBVTczRCIsImRiX25hbWUiOiJ6YWluX2luYXBwIiwiZGlzcGxheV9uYW1lIjoiemFpbl9pbmFwcCIsImVudmlyb25tZW50IjoibGl2ZSIsImlkIjoiNjM5ODUyZWViMGVjOWFiMzhhNzkyMTg5In0sImV4cCI6MTc3MTczMDIzOSwiaWF0IjoxNzY2NDc0MjM5LCJpc3MiOiJhcHAubW9lbmdhZ2UuY29tIiwibmJmIjoxNzY2NDc0MjM5LCJyb2xlIjoiQWRtaW4iLCJ1c2VyIjp7IjJGQSI6dHJ1ZSwiZW1haWwiOiJzd2V0YS5hZ2Fyd2FsQG1vZW5nYWdlLmNvbSIsImlkIjoiNjIxZGE5ZDlhMGRmOThmNDkwMzIyYjgzIiwibG9naW5fdHlwZSI6IlNURCJ9fQ.fT5PL9PSZcT17XS5YC5Cky5n9W6-KFaNiKGSlq3Fglag8X5UiUEg4egRYIhf4YoZ6KxiGC-ppxYrvhrV8vE0XKmBESLLbqvoPtJ_hO7iXdStlnmTdpW3cKY4cyZmT3tkfFqLoXJX7srFDgE-w1z-ytITuchcitYUyCVw-FRM5kCh7KSJihBP0HzBw_P82i9iJi-3t0OxIRilWc36FmMMVasYtz2_tM00DU9qNGMOmq6BUAg-OtHia5HiSq14j1xylH0rof4OOP4zHf1LVIf7cOj5htUQooucrtOJQUPfRwFWrCEJ_zFjOfg1fUJwzy9c05xv44tzeuQatU9HL1Li6g")
    
    if not session_id:
        return "", "Error: No Session ID provided."

    # Construct dynamic URL with the session_id
    # Format: .../stream?user_id=...&session_id=...&agent_id=...
    dynamic_url = API_URL.format(session_id)
    
    payload = {
        "payload": {
            "type": "user",
            "text": full_prompt
        }
    }
    
    # Headers
    request_headers = get_common_headers(auth_token)
    cookie_dict = get_cookies_dict()

    final_html = ""
    
    try:
        masked_token = auth_token[:10] + "..." if auth_token else "NONE"
        logger.info(f"API Call | Session: {session_id}")
        
        if cookie_dict:
             response = requests.post(dynamic_url, json=payload, headers=request_headers, cookies=cookie_dict, stream=True, timeout=900)
        else:
             response = requests.post(dynamic_url, json=payload, headers=request_headers, stream=True, timeout=900)
             
        with response:
            if response.status_code != 200:
                logger.error(f"MoEngage API Error {response.status_code}: {response.text[:200]}")
                final_html = ""
            last_seen_line = ""
            seen_structure_keys = set()
            longest_line_sample = ""
            content_debug_val = "" # To capture content value
                
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    last_seen_line = decoded_line 
                    
                    # Handle SSE format (remove "data: " prefix if present)
                    if decoded_line.startswith("data:"):
                        decoded_line = decoded_line[5:]
                        
                    if not decoded_line.strip():
                        continue
                        
                    try:
                        # Parse the JSON chunk
                        chunk_json = json.loads(decoded_line)
                        
                        # DEBUG: Collect keys
                        if isinstance(chunk_json, dict):
                             seen_structure_keys.update(chunk_json.keys())
                             if "payload" in chunk_json and isinstance(chunk_json["payload"], dict):
                                  seen_structure_keys.add(f"payload.{list(chunk_json['payload'].keys())}")
                        
                        # --- CRITICAL STEP: Extract from 'html' key ---
                        html_fragment = chunk_json.get("html")
                        
                        if not html_fragment and "payload" in chunk_json:
                             html_fragment = chunk_json["payload"].get("html")

                        # NEW: Check 'content' key (Corrected Path based on Debug Trace)
                        if not html_fragment and "content" in chunk_json:
                             content_val = chunk_json.get("content") or {}
                             # DEBUG Capture
                             if not content_debug_val: 
                                 content_debug_val = str(content_val)[:200]
                             
                             if isinstance(content_val, dict):
                                 # Path: content -> preview-payload -> data -> html
                                 preview_payload = content_val.get("preview-payload") or {}
                                 data_node = preview_payload.get("data") or {}
                                 html_fragment = data_node.get("html")
                                 
                                 # Fallback: maybe just content['html']?
                                 if not html_fragment:
                                     html_fragment = content_val.get("html")
                        
                        # Append if data was found
                        if html_fragment:
                            final_html += html_fragment
                            
                    except json.JSONDecodeError:
                        continue # Skipping non-JSON line

        if final_html:
            logger.info(f"Successfully extracted HTML from stream. Length: {len(final_html)}")
            return final_html, "Success: HTML Extracted"
        else:
            logger.warning("Stream finished but no HTML found.")
            # detailed debug message
            debug_msg = f"No HTML. Keys Seen: {list(seen_structure_keys)}. "
            if content_debug_val:
                debug_msg += f" ContentVal: {content_debug_val} "
            if 'last_seen_line' in locals():
                 debug_msg += f"Last Line: {last_seen_line[:200]}"
            return "", debug_msg
            
    except Exception as e:
        logger.error(f"Stream Request Failed: {e}", exc_info=True)
        return "", f"Exception: {str(e)}"
