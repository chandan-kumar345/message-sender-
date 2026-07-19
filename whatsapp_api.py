import requests
import os
import mimetypes
from pathlib import Path
import time
from typing import Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class WhatsAppClient:
    """Client for interacting with the official Meta WhatsApp Business Cloud API."""
    
    def __init__(self, access_token: str, phone_number_id: str, api_version: str = "v20.0"):
        self.access_token = access_token.strip()
        self.phone_number_id = phone_number_id.strip()
        self.api_version = api_version.strip()
        
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def is_configured(self) -> bool:
        """Checks if the client credentials are set."""
        return bool(self.access_token and self.phone_number_id)

    def _execute_request_with_retry(self, 
                                    method: str, 
                                    url: str, 
                                    retry_limit: int = 3, 
                                    **kwargs) -> requests.Response:
        """Executes an HTTP request with retry logic for network and rate-limit anomalies."""
        last_exception = None
        
        for attempt in range(1, retry_limit + 1):
            try:
                logger.info(f"API Request attempt {attempt} to {url}")
                response = requests.request(method, url, timeout=15, **kwargs)
                
                # Check for rate limit (429) or server errors (5xx)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limit hit (429). Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                    
                if 500 <= response.status_code < 600:
                    logger.warning(f"Server error {response.status_code}. Retrying in {attempt * 2}s...")
                    time.sleep(attempt * 2)
                    continue
                    
                return response
                
            except requests.exceptions.Timeout as te:
                logger.warning(f"Request timeout on attempt {attempt}: {te}")
                last_exception = te
                time.sleep(attempt * 2)
            except requests.exceptions.RequestException as re:
                logger.error(f"Network error on attempt {attempt}: {re}")
                last_exception = re
                time.sleep(attempt * 2)
                
        if last_exception:
            raise last_exception
        raise requests.exceptions.RequestException("Request failed after max retries due to unknown reasons.")

    def upload_media(self, file_path: str, retry_limit: int = 3) -> Tuple[bool, str, str]:
        """
        Uploads a local media file (Image, PDF, brochure) to Meta's servers.
        
        Returns:
            Tuple[bool, media_id, error_message]
        """
        path = Path(file_path)
        if not path.exists():
            return False, "", f"File not found: {file_path}"
            
        file_size = path.stat().st_size
        # Meta limits: check file size (typically max 100MB for docs, 5MB for images in Cloud API)
        if file_size > 100 * 1024 * 1024:
            return False, "", f"File size too large: {file_size / (1024*1024):.2f}MB. Max is 100MB."

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        url = f"{self.base_url}/media"
        
        # Override headers for multipart/form-data (requests handles boundary automatically if we don't set Content-Type header)
        upload_headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            with open(path, "rb") as f:
                files = {
                    "file": (path.name, f, mime_type),
                }
                data = {
                    "messaging_product": "whatsapp"
                }
                
                response = self._execute_request_with_retry(
                    "POST", 
                    url, 
                    retry_limit=retry_limit, 
                    headers=upload_headers, 
                    files=files, 
                    data=data
                )
                
                res_data = response.json()
                if response.status_code == 200 and "id" in res_data:
                    return True, res_data["id"], ""
                else:
                    err_msg = res_data.get("error", {}).get("message", f"Status code: {response.status_code}")
                    return False, "", f"Meta Upload Error: {err_msg}"
                    
        except Exception as e:
            logger.error(f"Failed to upload media {file_path}: {e}")
            return False, "", str(e)

    def send_text_message(self, to_phone: str, text: str, retry_limit: int = 3) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Sends a standard text message.
        
        Returns:
            Tuple[bool, wamid, response_json]
        """
        url = f"{self.base_url}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text
            }
        }
        
        return self._send_api_payload(url, payload, retry_limit)

    def send_media_message(self, 
                           to_phone: str, 
                           media_id: str, 
                           file_path: str, 
                           caption: str = "", 
                           retry_limit: int = 3) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Sends an uploaded media message (Image or Document) using its media ID.
        
        Returns:
            Tuple[bool, wamid, response_json]
        """
        url = f"{self.base_url}/messages"
        path = Path(file_path)
        
        mime_type, _ = mimetypes.guess_type(file_path)
        media_type = "document"
        if mime_type and mime_type.startswith("image/"):
            media_type = "image"
            
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": media_type
        }
        
        if media_type == "image":
            payload["image"] = {
                "id": media_id
            }
            if caption:
                payload["image"]["caption"] = caption
        else: # document
            payload["document"] = {
                "id": media_id,
                "filename": path.name
            }
            if caption:
                payload["document"]["caption"] = caption
                
        return self._send_api_payload(url, payload, retry_limit)

    def _send_api_payload(self, url: str, payload: Dict[str, Any], retry_limit: int) -> Tuple[bool, str, Dict[str, Any]]:
        """Sends the JSON payload to Meta APIs and parses output."""
        try:
            response = self._execute_request_with_retry(
                "POST", 
                url, 
                retry_limit=retry_limit, 
                headers=self.headers, 
                json=payload
            )
            
            res_data = response.json()
            if response.status_code == 200:
                # Success
                messages = res_data.get("messages", [])
                wamid = messages[0].get("id", "unknown_id") if messages else "unknown_id"
                return True, wamid, res_data
            else:
                err_info = res_data.get("error", {})
                err_msg = err_info.get("message", "Unknown API error")
                err_code = err_info.get("code", "N/A")
                return False, f"API Error {err_code}: {err_msg}", res_data
                
        except Exception as e:
            logger.error(f"Failed to execute API send: {e}")
            return False, str(e), {"error": str(e)}
            
    def test_connection(self) -> Tuple[bool, str]:
        """Tests the token and API validity by making a lightweight query to the API (fetching details of the phone ID)."""
        # Fetching registration details of the phone ID is a safe read operation that checks permissions and token validity
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            res_data = response.json()
            
            if response.status_code == 200:
                return True, f"Connection successful. Registered number: {res_data.get('display_phone_number', 'N/A')}"
            else:
                err_info = res_data.get("error", {})
                err_msg = err_info.get("message", "Unauthorized")
                err_code = err_info.get("code", "N/A")
                # Specific check for invalid token
                if err_code == 190:
                    return False, "Invalid Access Token. Please update in settings."
                return False, f"API test failed (Code {err_code}): {err_msg}"
        except Exception as e:
            return False, f"Connection timeout or network failure: {str(e)}"
