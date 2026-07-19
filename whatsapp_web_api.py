import os
import time
import urllib.parse
import urllib.request
import json
import base64
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import logging
import websocket  # from websocket-client

logger = logging.getLogger(__name__)

class WhatsAppWebClient:
    """Client for automating WhatsApp Web headlessly using Chrome DevTools Protocol (CDP) over WebSockets."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.session_dir = base_dir / ".whatsapp_session"
        self.proc: Optional[subprocess.Popen] = None
        self.ws: Optional[websocket.WebSocket] = None
        self.cmd_id = 0

    def is_configured(self) -> bool:
        """WhatsApp Web doesn't need API token settings, so it is always ready to connect."""
        return True

    def _find_chrome_path(self) -> Path:
        """Locates the Google Chrome executable on standard Windows installation paths."""
        paths = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / r"Google\Chrome\Application\chrome.exe"
        ]
        for p in paths:
            if p.exists():
                return p
        raise FileNotFoundError("Google Chrome was not found in standard installation paths.")

    def is_browser_running(self) -> bool:
        """Checks if the Chrome process is active."""
        if not self.proc:
            return False
        # poll() returns None if process is still running
        if self.proc.poll() is None:
            return True
        self.proc = None
        return False

    def _kill_orphaned_chrome(self) -> None:
        """Kills any orphaned headless Chrome processes using remote debugging port 9222 to free the profile lock."""
        try:
            cmd = (
                "Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" | "
                "Where-Object { $_.CommandLine -like \"*--remote-debugging-port=9222*\" } | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
            )
            subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, check=False)
            time.sleep(1) # Give OS a moment to release file handles
        except Exception as e:
            logger.warning(f"Failed to kill orphaned Chrome processes: {e}")

    def start_browser(self) -> Tuple[bool, str]:
        """Launches Google Chrome headlessly with debugging enabled on port 9222."""
        if self.is_browser_running():
            return True, "Browser is already running."
            
        try:
            self._kill_orphaned_chrome()
            chrome_path = self._find_chrome_path()
            profile_path = self.session_dir / "profile"
            profile_path.mkdir(parents=True, exist_ok=True)
            
            # Start Chrome directly
            self.proc = subprocess.Popen([
                str(chrome_path),
                "--remote-debugging-port=9222",
                f"--user-data-dir={profile_path.resolve()}",
                "--headless=new",
                "--window-size=1400,1050",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--remote-allow-origins=*"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait for browser to start up and listen on port
            time.sleep(3)
            
            # Initialize WebSocket connection
            self._get_ws()
            return True, "Browser started successfully."
        except Exception as e:
            logger.error(f"Failed to launch Chrome: {e}")
            self.close_browser()
            return False, f"Launch Error: {str(e)}"

    def _get_ws(self) -> websocket.WebSocket:
        """Connects or reconnects to Chrome over DevTools WebSocket protocol."""
        if self.ws and self.is_browser_running() and getattr(self.ws, "connected", False):
            return self.ws
            
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

        if not self.is_browser_running():
            raise Exception("Browser process is not running.")

        try:
            url = "http://127.0.0.1:9222/json"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                tabs = json.loads(response.read().decode())
                
            page_tabs = [t for t in tabs if t.get("type") == "page"]
            if not page_tabs:
                raise Exception("No active browser tabs found.")
                
            ws_url = page_tabs[0]["webSocketDebuggerUrl"]
            self.ws = websocket.create_connection(ws_url, timeout=15)
            self.cmd_id = 0
            return self.ws
        except Exception as e:
            logger.error(f"Failed to connect to debugger WebSocket: {e}")
            raise e

    def send_command(self, method: str, params: Optional[dict] = None, timeout: int = 15) -> Any:
        """Sends a JSON-RPC command to Chrome over the WebSocket connection."""
        ws = self._get_ws()
        if not ws:
            raise Exception("WebSocket connection is not established.")
            
        self.cmd_id += 1
        cmd_id = self.cmd_id
        
        payload = {
            "id": cmd_id,
            "method": method,
            "params": params or {}
        }
        
        ws.settimeout(timeout)
        ws.send(json.dumps(payload))
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                res = json.loads(ws.recv())
                if "id" in res and res["id"] == cmd_id:
                    if "error" in res:
                        raise Exception(f"CDP Error: {res['error']}")
                    return res.get("result")
            except websocket.WebSocketTimeoutException:
                raise TimeoutError(f"CDP command '{method}' timed out.")
            except Exception as e:
                raise e
        raise TimeoutError(f"CDP command '{method}' timed out.")

    def evaluate_js(self, expression: str) -> Any:
        """Evaluates Javascript inside the active page context and returns the result."""
        try:
            res = self.send_command("Runtime.evaluate", {
                "expression": expression,
                "returnByValue": True
            })
            return res.get("result", {}).get("value")
        except Exception as e:
            logger.error(f"CDP JS Eval Error on '{expression[:60]}': {e}")
            return None

    def check_login_status(self) -> Tuple[bool, str]:
        """Checks the login state of the WhatsApp Web application."""
        if not self.is_browser_running():
            return False, "Browser Closed"
            
        try:
            # Check for chat pane or search element
            is_connected = self.evaluate_js(
                "!!document.querySelector('#pane-side') || !!document.querySelector('span[data-testid=\"search\"]')"
            )
            if is_connected:
                return True, "Connected"
                
            # Check for canvas QR element
            has_canvas = self.evaluate_js("!!document.querySelector('canvas')")
            if has_canvas:
                return False, "Scan QR Code"
                
            return False, "Connecting..."
        except Exception:
            return False, "Connecting..."

    def test_connection(self) -> Tuple[bool, str]:
        """Validates connection by querying the current page status."""
        if not self.is_browser_running():
            return False, "Browser is not running. Click 'Start WhatsApp Web Connection' first."
            
        is_logged_in, status = self.check_login_status()
        if is_logged_in:
            return True, "WhatsApp Web: Connected and authenticated."
        else:
            if status == "Scan QR Code":
                return False, "WhatsApp Web: Waiting for QR scan. Please scan the QR code displayed."
            return False, f"WhatsApp Web Status: {status}"

    def capture_qr_code(self, save_path: Path) -> Tuple[bool, str]:
        """Captures a clip screenshot of the QR code canvas element directly."""
        if not self.is_browser_running():
            return False, "Browser Closed"
            
        try:
            # Retrieve bounding box of canvas element
            box = self.evaluate_js("""
                (function() {
                    var el = document.querySelector('canvas');
                    if (!el) return null;
                    var rect = el.getBoundingClientRect();
                    return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
                })()
            """)
            
            if not box:
                return False, "QR Canvas element not loaded yet."
                
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Take screenshot of coordinates
            clip = {
                "x": box["x"],
                "y": box["y"],
                "width": box["width"],
                "height": box["height"],
                "scale": 1
            }
            res = self.send_command("Page.captureScreenshot", {
                "format": "png",
                "clip": clip
            })
            
            img_data = base64.b64decode(res["data"])
            with open(save_path, "wb") as f:
                f.write(img_data)
                
            return True, ""
        except Exception as e:
            return False, str(e)

    def send_text_message(self, to_phone: str, text: str, retry_limit: int = 3) -> Tuple[bool, str, Dict[str, Any]]:
        """Sends a text message using direct URL dispatch and JavaScript click automation."""
        if not self.is_browser_running():
            return False, "Browser Closed", {"error": "Browser is not running."}
            
        try:
            clean_phone = "".join(filter(str.isdigit, to_phone))
            encoded_text = urllib.parse.quote(text)
            url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
            
            self.send_command("Page.navigate", {"url": url})
            
            start_time = time.time()
            send_btn_ready = False
            is_invalid = False
            
            while time.time() - start_time < 35:
                if not self.is_browser_running():
                    return False, "Browser Closed during send", {"error": "Browser Closed"}
                    
                # 1. Check if Send button is clickable
                send_btn_ready = self.evaluate_js(
                    "var b = document.querySelector('span[data-testid=\"send\"]') || document.querySelector('button[aria-label=\"Send\"]'); "
                    "!!b && b.offsetWidth > 0 && b.offsetHeight > 0"
                )
                if send_btn_ready:
                    break
                    
                # 2. Check for invalid phone number popup
                is_invalid = self.evaluate_js(
                    "document.body.innerText.includes('phone number shared via url is invalid') || "
                    "document.body.innerText.includes('Phone number shared via url is invalid') || "
                    "document.body.innerText.includes('invalid phone number')"
                )
                if is_invalid:
                    break
                    
                time.sleep(1)
                
            if is_invalid:
                # Dismiss dialog by clicking OK button if it exists
                self.evaluate_js(
                    "var btn = document.querySelector('button[span[contains(text(), \"OK\")]]') || "
                    "document.querySelector('button') || document.querySelector('div[role=\"button\"]'); "
                    "if (btn) btn.click();"
                )
                return False, "Invalid number", {"error": "Phone number is not registered on WhatsApp."}
                
            if not send_btn_ready:
                return False, "Timeout loading chat page", {"error": "Page took too long to load."}
                
            # Click send button
            self.evaluate_js(
                "(document.querySelector('span[data-testid=\"send\"]') || "
                "document.querySelector('button[aria-label=\"Send\"]')).click()"
            )
            time.sleep(4) # Give it 4 seconds to dispatch the text
            
            wamid = f"web_{int(time.time())}"
            return True, wamid, {"method": "web"}
            
        except Exception as e:
            logger.error(f"Error during CDP text dispatch: {e}")
            return False, str(e), {"error": str(e)}

    def send_media_message(self, 
                           to_phone: str, 
                           media_id: str, 
                           file_path: str, 
                           caption: str = "", 
                           retry_limit: int = 3) -> Tuple[bool, str, Dict[str, Any]]:
        """Sends a media file by injecting it directly into the DOM file input and automating send."""
        if not self.is_browser_running():
            return False, "Browser Closed", {"error": "Browser is not running."}
            
        path = Path(file_path)
        if not path.exists():
            return False, "File Not Found", {"error": f"File does not exist: {file_path}"}
            
        try:
            clean_phone = "".join(filter(str.isdigit, to_phone))
            url = f"https://web.whatsapp.com/send?phone={clean_phone}"
            
            self.send_command("Page.navigate", {"url": url})
            
            start_time = time.time()
            chat_loaded = False
            is_invalid = False
            
            # Wait for chat input area to load
            while time.time() - start_time < 35:
                if not self.is_browser_running():
                    return False, "Browser Closed during load", {"error": "Browser Closed"}
                    
                chat_loaded = self.evaluate_js("!!document.querySelector('div[contenteditable=\"true\"]')")
                if chat_loaded:
                    break
                    
                is_invalid = self.evaluate_js(
                    "document.body.innerText.includes('phone number shared via url is invalid') || "
                    "document.body.innerText.includes('Phone number shared via url is invalid') || "
                    "document.body.innerText.includes('invalid phone number')"
                )
                if is_invalid:
                    break
                    
                time.sleep(1)
                
            if is_invalid:
                try:
                    self.evaluate_js("var btn = document.querySelector('button'); if (btn) btn.click();")
                except Exception:
                    pass
                return False, "Invalid number", {"error": "Phone number is not registered on WhatsApp."}
                
            if not chat_loaded:
                return False, "Timeout loading chat page", {"error": "Chat interface took too long to load."}
                
            # Enable DOM domain
            self.send_command("DOM.enable")
            
            # Query selector input[type="file"]
            doc = self.send_command("DOM.getDocument")
            root_node_id = doc["root"]["nodeId"]
            
            # We try querying selector 'input[type="file"]'
            res = self.send_command("DOM.querySelector", {
                "nodeId": root_node_id,
                "selector": "input[type='file']"
            })
            node_id = res.get("nodeId", 0)
            if not node_id:
                return False, "File upload input element missing", {"error": "Could not find file input in DOM."}
                
            # Set files
            self.send_command("DOM.setFileInputFiles", {
                "nodeId": node_id,
                "files": [str(path.resolve())]
            })
            
            # Wait for the media send button to appear on the preview page
            start_time = time.time()
            preview_ready = False
            media_send_xpath = "var b = document.querySelector('span[data-testid=\"send\"]') || document.querySelector('div[aria-label=\"Send\"]') || document.querySelector('button[aria-label=\"Send\"]'); !!b && b.offsetWidth > 0"
            
            while time.time() - start_time < 15:
                preview_ready = self.evaluate_js(media_send_xpath)
                if preview_ready:
                    break
                time.sleep(1)
                
            if not preview_ready:
                return False, "Timeout loading media preview", {"error": "Media preview took too long to render."}
                
            # Input caption if provided
            if caption:
                self.evaluate_js(f"""
                    (function() {{
                        var el = document.querySelector('div[contenteditable="true"][data-tab="10"]') || 
                                 document.querySelector('div[contenteditable="true"][role="textbox"]') ||
                                 document.querySelector('div[contenteditable="true"]');
                        if (el) {{
                            el.focus();
                            document.execCommand('insertText', false, {json.dumps(caption)});
                        }}
                    }})()
                """)
                time.sleep(1)
                
            # Click send button
            self.evaluate_js(
                "(document.querySelector('span[data-testid=\"send\"]') || "
                "document.querySelector('div[aria-label=\"Send\"]') || "
                "document.querySelector('button[aria-label=\"Send\"]')).click()"
            )
            time.sleep(6) # Give it 6 seconds to complete media transmission
            
            wamid = f"web_media_{int(time.time())}"
            return True, wamid, {"method": "web"}
            
        except Exception as e:
            logger.error(f"Error during CDP media dispatch: {e}")
            return False, str(e), {"error": str(e)}

    def close_browser(self):
        """Closes the WebSocket connection and terminates the Chrome process."""
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
            
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
