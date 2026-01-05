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
API_URL = f"{API_BASE}/response/stream?user_id=kaushiki.vajpayee@moengage.com&session_id={{}}&agent_id=inapp-html-ai-v1"
SESSION_URL = f"{API_BASE}/sessions"

# Headers from User CURL
# Note: In a real prod env, these should be rotated and loaded from secrets.
HEADERS = {
    "accept": "application/json",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "content-type": "application/json",
    # "authorization": "Bearer ...", # Loaded from env or fallback
    "moetraceid": "1eb63886-79d0-4210-9e76-c4974a940550",
    "origin": "https://html-ai-template.moestaging.com",
    "page": "inapp/create/",
    "priority": "u=1, i",
    "refreshtoken": "34cfe549-f0b4-46a2-94db-b2ceed7391d2",
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
    cookies_header = os.environ.get("MOENGAGE_COOKIES", "moe_c_s=1; moe_uuid=303a6077-185f-472c-b8fe-89b42ff438a0; moe_u_d=HcdRCoAgDADQu-y7QWMa2mVEtwmBEGR-RXdP-nwP9HQ2hb3m1m0BTVnVpu9r_BzHBFDJKkyMXMSjC1vFQMZopD56F5VXgfcD; moe_s_n=Rco7DoMwEEXRvUyNpYnt-ZitRNEoEEdCCChMh9g7Ng3lu-8cUGyGHlCGX4rk3YABXfzz6FRDcJpFfPZfFCToKi62Q_8SFlJOnhlTq8tdFbGD0Sbb23x_2pMfr0IcqfrVNiu1nhc")
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
    auth_token = os.environ.get("MOENGAGE_BEARER_TOKEN", "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE1NzI1MTI0NTciLCJ0eXAiOiJKV1QifQ.eyJhcHAiOnsiYXBwX2tleSI6IkNNNEQxTFpOMklNSk5CWTlVTFhBVTczRCIsImRiX25hbWUiOiJ6YWluX2luYXBwIiwiZGlzcGxheV9uYW1lIjoiemFpbl9pbmFwcCIsImVudmlyb25tZW50IjoibGl2ZSIsImlkIjoiNjM5ODUyZWViMGVjOWFiMzhhNzkyMTg5In0sImV4cCI6MTc3Mjg0MjkzOCwiaWF0IjoxNzY3NTg2OTM4LCJpc3MiOiJhcHAubW9lbmdhZ2UuY29tIiwibmJmIjoxNzY3NTg2OTM4LCJyb2xlIjoiQWRtaW4iLCJ1c2VyIjp7ImVtYWlsIjoiYXJpaml0LmRhc0Btb2VuZ2FnZS5jb20iLCJpZCI6IjYzZGNlZjg3ODBlOTM3Yjg5YzE0Y2IzNyIsImxvZ2luX3R5cGUiOiJTVEQifX0.bK639O6rZgsDR3uiBcLAFnBI8u35gFdDVBmvkIqgVcW63NkI4s8JrxvJf4p_GMu3x9g9AtcaIxDndtWnQhMDCxYzHnPIbkOHL_ewBoWqFG5nC1ZIQyX0YlNdEi1lYgAm09FLMjKvJjmZoTDwgMYfOdDXYxYgZ2EsGTEOb-u_CTXzJ4YBjlvAl85kYampUVARgD1jtGY_3wR0X9uBY11zeb3yaVU96fGEPjoLbPNN8uNXlquBtMiedzphdsBmY3z9amQ89PpFqdfN1rVBQvrMeQwmSzPfVUyzL857yrH4RvfuSnuYiiRIyDrpaalQLAIfviSYb406p1P76Ik02KvyGw")
    
    headers = get_common_headers(auth_token)
    cookie_dict = get_cookies_dict()
    
    # Payload for session creation (from CURL)
    payload = {"user_id": "kaushiki.vajpayee@moengage.com", "agent_id": "inapp-html-ai-v1"}
    
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
    
    auth_token = os.environ.get("MOENGAGE_BEARER_TOKEN", "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE1NzI1MTI0NTciLCJ0eXAiOiJKV1QifQ.eyJhcHAiOnsiYXBwX2tleSI6IkNNNEQxTFpOMklNSk5CWTlVTFhBVTczRCIsImRiX25hbWUiOiJ6YWluX2luYXBwIiwiZGlzcGxheV9uYW1lIjoiemFpbl9pbmFwcCIsImVudmlyb25tZW50IjoibGl2ZSIsImlkIjoiNjM5ODUyZWViMGVjOWFiMzhhNzkyMTg5In0sImV4cCI6MTc3MjMzNDc3NSwiaWF0IjoxNzY3MDc4Nzc1LCJpc3MiOiJhcHAubW9lbmdhZ2UuY29tIiwibmJmIjoxNzY3MDc4Nzc1LCJyb2xlIjoiQWRtaW4iLCJ1c2VyIjp7ImVtYWlsIjoia2F1c2hpa2kudmFqcGF5ZWVAbW9lbmdhZ2UuY29tIiwiaWQiOiI2NDQyNDE0NjBlOTM0Mjg1ZDMzNDJiYzEiLCJsb2dpbl90eXBlIjoiU1REIn19.eajLu_gRNTTvDd3uaQYVO5zSXRfu5SoGjMkZfni-K0yH3XP_CgWIPj0njinHaRU2bfNtDnKpM5p5EIyOoH9GqQQL4TGyCrLMneZA-5RIzRNs0itGKi57JoPtgR1Bx9umvPQrfxWtwZqRy_s1XXianfYblOGVyfc-SQAawn4IWrM7GEtkZe_INvf7FdvTaROkjIF8mO66to5z23eJC_MghxRdDY2nPVHPkIvrmBKumz8zatMEXTvcdC63ubiakEgdkX9HwtVy-niwKYB2ax39XQlWfE4YoYP2-bY6cM4JEzU4piYJcgZiiz7E09VRi_txUgklrhwqBGs_a4a1dH0WGQ")
    
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
