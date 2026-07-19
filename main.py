import sys
import os
import time
import threading
from pathlib import Path
from datetime import datetime
import shutil
from typing import Dict, Any, List, Optional
from tkinter import messagebox

# Import core modules
from settings import Settings
from utils import play_notification_sound, clean_phone_number, validate_and_format_phone
from excel_reader import ExcelReader
from template_manager import TemplateManager
from logger import WhatsAppLogger
from whatsapp_api import WhatsAppClient
from gui import WhatsAppSenderGUI

class WhatsAppCampaignController:
    """Orchestrates application modules, GUI callbacks, and campaign dispatch threads."""
    
    def __init__(self):
        # 1. Initialize core system modules
        self.base_dir = Path(__file__).resolve().parent
        self.settings = Settings(self.base_dir)
        self.tpl_manager = TemplateManager(self.base_dir / "templates")
        self.logger = WhatsAppLogger(self.base_dir)
        
        # Initialize API client
        self.api_client = WhatsAppClient(
            access_token=self.settings.access_token,
            phone_number_id=self.settings.phone_number_id,
            api_version=self.settings.api_version
        )
        
        # 2. Instantiate GUI
        self.gui = WhatsAppSenderGUI(self.settings)
        
        # 3. Campaign state parameters
        self.is_sending = False
        self.is_paused = False
        self.stop_requested = False
        self.campaign_thread: Optional[threading.Thread] = None
        
        # 4. Map GUI callbacks
        self._register_callbacks()
        
        # 5. Perform startup tasks
        self._on_startup()

    def _register_callbacks(self) -> None:
        """Binds controller handlers onto GUI interactive events."""
        self.gui.set_callback("import_leads", self.handle_import_leads)
        self.gui.set_callback("add_manual_lead", self.handle_add_manual_lead)
        self.gui.set_callback("replace_placeholders", self.tpl_manager.replace_placeholders)
        
        # Campaign control triggers
        self.gui.set_callback("start_campaign", self.handle_start_campaign)
        self.gui.set_callback("pause_campaign", self.handle_pause_campaign)
        self.gui.set_callback("stop_campaign", self.handle_stop_campaign)
        
        # Templates operations
        self.gui.set_callback("refresh_templates", self.refresh_templates_views)
        self.gui.set_callback("load_template_to_editor", self.handle_load_template_to_editor)
        self.gui.set_callback("load_template_to_composer", self.handle_load_template_to_composer)
        self.gui.set_callback("save_template", self.handle_save_template)
        self.gui.set_callback("delete_template", self.handle_delete_template)
        
        # Logs operations
        self.gui.set_callback("refresh_logs", self.refresh_logs_console)
        self.gui.set_callback("export_logs", self.handle_export_logs)
        self.gui.set_callback("export_filtered_leads", self.handle_export_filtered_leads)
        
        # Settings operations
        self.gui.set_callback("test_api_connection", self.handle_test_api_connection)
        self.gui.set_callback("save_settings", self.handle_save_settings)
        self.gui.set_callback("save_logo", self.handle_save_logo)
        
        # Dashboard refresh trigger
        self.gui.set_callback("refresh_dashboard", self.refresh_dashboard_stats)

    def _on_startup(self) -> None:
        """Executes startup configuration alignment checks."""
        self.logger.log_transmission("System", "00", "App initiated.", "Info")
        self.gui.append_log("Application launched successfully.")
        
        # Load custom company logo if exists
        logo_path = self.base_dir / "assets" / "logo.png"
        if logo_path.exists():
            self.gui.load_company_logo(str(logo_path))
            
        # Refresh templates UI
        self.refresh_templates_views()
        
        # Verify connection details asynchronously to keep startup fast
        threading.Thread(target=self._check_api_connectivity_background, daemon=True).start()

    def _check_api_connectivity_background(self) -> None:
        """Checks WhatsApp credentials status in the background and updates the GUI."""
        if not self.api_client.is_configured():
            self.gui.update_connection_status_lbl("No API credentials configured. Enter them in Settings.", success=False)
            return
            
        self.gui.update_connection_status_lbl("Connecting to WhatsApp API...", success=True)
        success, msg = self.api_client.test_connection()
        self.gui.update_connection_status_lbl(msg, success=success)

    # =========================================================================
    # CORE HANDLER FUNCTIONS
    # =========================================================================

    def refresh_dashboard_stats(self) -> None:
        """Aggregates sending status matrices and updates Dashboard."""
        leads = self.gui.leads_data
        
        total = len(leads)
        selected = sum(1 for l in leads if l.get("selected", False))
        
        sent = sum(1 for l in leads if l["status"].lower() == "sent")
        failed = sum(1 for l in leads if l["status"].lower() == "failed")
        
        # Pending is selected but not sent/failed
        pending = sum(1 for l in leads if l.get("selected", False) and l["status"].lower() in ["pending", "queued"])
        
        # Calculate success rate
        completed = sent + failed
        rate_val = (sent / completed * 100) if completed > 0 else 0.0
        success_rate = f"{rate_val:.1f}%"
        
        stats = {
            "total": total,
            "selected": selected,
            "sent": sent,
            "failed": failed,
            "pending": pending,
            "success_rate": success_rate
        }
        
        self.gui.update_dashboard_metrics(stats)

    def handle_import_leads(self, file_path: str) -> None:
        """Imports leads spreadsheet, updates GUI table, logs anomalies."""
        self.gui.append_log(f"Reading file: {file_path}")
        
        try:
            leads, warnings = ExcelReader.read_file(file_path)
            
            # Log any minor warnings generated during parse
            for warning in warnings:
                self.gui.append_log(f"Warning: {warning}")
                
            self.gui.display_leads_table(leads)
            
            valid_count = sum(1 for l in leads if l["is_valid"])
            duplicate_count = sum(1 for l in leads if l.get("is_duplicate", False))
            invalid_count = len(leads) - valid_count - duplicate_count
            
            self.gui.append_log(
                f"Import complete: {len(leads)} rows loaded. "
                f"Valid: {valid_count} | Duplicates: {duplicate_count} | Invalid: {invalid_count}"
            )
            
            # Refresh statistics
            self.refresh_dashboard_stats()
            
        except Exception as e:
            self.gui.append_log(f"Import Failed: {e}")
            messagebox.showerror("Import Failed", f"Could not read spreadsheet file:\n{str(e)}")

    def handle_add_manual_lead(self, phone: str, name: str, email: str, company: str, date: str) -> tuple[bool, str]:
        """Manually creates a lead entry and inserts it into the table."""
        # 1. Clean and validate phone
        valid, formatted_phone = validate_and_format_phone(phone)
        if not valid:
            return False, f"Invalid phone format: '{phone}'."
            
        # 2. Duplicate check in the existing leads list
        for lead in self.gui.leads_data:
            if lead["phone"] == formatted_phone and lead["is_valid"]:
                return False, f"Lead with phone number '{formatted_phone}' already exists."
                
        # 3. Create lead dictionary
        new_lead = {
            "name": name.strip() or "Lead", # Default to 'Lead' if empty
            "phone": formatted_phone,
            "original_phone": phone.strip(),
            "email": email.strip(),
            "company": company.strip(),
            "status": "Pending",
            "last_contact_date": date.strip() or datetime.now().strftime("%Y-%m-%d"),
            "is_valid": True,
            "validation_error": "",
            "is_duplicate": False,
            "selected": True # Automatically select manually added leads
        }
        
        # 4. Append to leads list and refresh GUI table
        self.gui.leads_data.append(new_lead)
        self.gui.display_leads_table(self.gui.leads_data)
        self.refresh_dashboard_stats()
        self.gui.append_log(f"Manually added lead: {new_lead['name']} ({new_lead['phone']})")
        
        return True, ""

    def refresh_templates_views(self) -> None:
        """Reloads stored template files onto manager lists and composer selectors."""
        templates = self.tpl_manager.load_templates()
        names = [t["name"] for t in templates]
        
        self.gui.populate_templates_dropdown(names)
        self.gui.update_templates_listbox(names)

    def handle_load_template_to_editor(self, tpl_name: str) -> None:
        """Fills template manager form columns when a template list item is clicked."""
        templates = self.tpl_manager.load_templates()
        for t in templates:
            if t["name"] == tpl_name:
                self.gui.fill_template_editor(t["name"], t["body"])
                break

    def handle_load_template_to_composer(self, tpl_name: str) -> None:
        """Loads selected template text content into Campaign Manager text editor."""
        templates = self.tpl_manager.load_templates()
        for t in templates:
            if t["name"] == tpl_name:
                self.gui.txt_message.configure(state="normal")
                self.gui.txt_message.delete("1.0", "end")
                self.gui.txt_message.insert("1.0", t["body"])
                self.gui._update_message_preview(self.gui.current_preview_index)
                self.gui.append_log(f"Loaded template '{tpl_name}' to composer.")
                break

    def handle_save_template(self, name: str, body: str) -> None:
        """Saves current template text input to local JSON store."""
        success, msg = self.tpl_manager.save_template(name, body)
        if success:
            self.gui.append_log(msg)
            self.refresh_templates_views()
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showwarning("Validation Error", msg)

    def handle_delete_template(self, name: str) -> None:
        """Removes the template from storage."""
        success, msg = self.tpl_manager.delete_template(name)
        if success:
            self.gui.append_log(msg)
            self.gui._on_new_template_click()  # Clear fields
            self.refresh_templates_views()
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showwarning("Error", msg)

    def refresh_logs_console(self) -> None:
        """Refreshes or prints active log metrics."""
        pass

    def handle_export_logs(self, export_path: str) -> None:
        """Exports general WhatsApp dispatch transaction records to Excel."""
        success = self.logger.export_history_to_excel(export_path)
        if success:
            self.gui.append_log(f"Exported sending logs to: {export_path}")
            messagebox.showinfo("Export Successful", f"WhatsApp log history saved to:\n{export_path}")
        else:
            messagebox.showwarning("Export Failed", "Could not export logs. File might be open or empty.")

    def handle_export_filtered_leads(self, status: str, export_path: str) -> None:
        """Exports campaign rows with specific statuses to Excel reports."""
        try:
            ExcelReader.export_report(self.gui.leads_data, export_path, filter_status=status)
            self.gui.append_log(f"Saved {status} report to: {export_path}")
            messagebox.showinfo("Export Successful", f"Saved campaign '{status}' list to:\n{export_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def handle_test_api_connection(self, token: str, phone_id: str, version: str) -> None:
        """Tests credentials validities asynchronously."""
        def run_test():
            client = WhatsAppClient(access_token=token, phone_number_id=phone_id, api_version=version)
            success, msg = client.test_connection()
            
            # Update GUI safely
            self.gui.btn_test_conn.configure(state="normal", text="⚡ Test API Connection")
            self.gui.update_connection_status_lbl(msg, success=success)
            
            if success:
                messagebox.showinfo("Connection Success", msg)
            else:
                messagebox.showerror("Connection Failed", msg)
                
        threading.Thread(target=run_test, daemon=True).start()

    def handle_save_settings(self, token: str, phone_id: str, version: str, sound: bool, retry: int) -> None:
        """Saves config variables and rebuilds the api_client instance."""
        delay = int(self.gui.slider_delay.get())
        
        self.settings.save(
            access_token=token,
            phone_number_id=phone_id,
            api_version=version,
            play_sound=sound,
            retry_limit=retry,
            sender_delay=delay
        )
        
        # Re-initialize client
        self.api_client = WhatsAppClient(
            access_token=self.settings.access_token,
            phone_number_id=self.settings.phone_number_id,
            api_version=self.settings.api_version
        )
        
        # Recheck connectivity
        threading.Thread(target=self._check_api_connectivity_background, daemon=True).start()
        
        self.gui.append_log("Application configuration updated successfully.")
        messagebox.showinfo("Success", "Settings updated successfully!")

    def handle_save_logo(self, source_logo_path: str) -> None:
        """Saves custom company logo file."""
        try:
            dest_dir = self.base_dir / "assets"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_logo = dest_dir / "logo.png"
            
            shutil.copy2(source_logo_path, dest_logo)
            self.gui.load_company_logo(str(dest_logo))
            self.gui.append_log(f"Company logo updated to: {dest_logo}")
            messagebox.showinfo("Success", "Logo updated successfully!")
        except Exception as e:
            self.gui.append_log(f"Failed to update company logo: {e}")
            messagebox.showerror("Upload Error", f"Could not update logo image:\n{str(e)}")

    # =========================================================================
    # CAMPAIGN SENDER EXECUTION LOGIC (WITH THREADING)
    # =========================================================================

    def handle_start_campaign(self) -> None:
        """Validates variables and kicks off dispatch sequence in a background thread."""
        # 1. Validation checks
        if self.is_sending:
            return
            
        if not self.api_client.is_configured():
            messagebox.showerror("Settings Incomplete", "Please configure WhatsApp API settings first.")
            self.gui.select_tab("settings")
            return
            
        selected_leads = [l for l in self.gui.leads_data if l.get("selected", False)]
        if not selected_leads:
            messagebox.showwarning("Empty Queue", "No leads selected. Check checkboxes in the lead list.")
            return
            
        template_body = self.gui.txt_message.get("1.0", "end").strip()
        if not template_body:
            messagebox.showwarning("Message Required", "Please compose a template message first.")
            return

        # Check for scheduling requirements
        schedule_time = None
        if self.gui.chk_sched_var.get():
            date_str = self.gui.ent_sched_date.get().strip()
            time_str = self.gui.ent_sched_time.get().strip()
            
            try:
                schedule_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                if schedule_time < datetime.now():
                    messagebox.showerror("Scheduling Error", "Scheduled date/time must be in the future.")
                    return
            except ValueError:
                messagebox.showerror(
                    "Scheduling Error", 
                    "Invalid Date/Time formats.\nExpected formats:\nDate: YYYY-MM-DD\nTime: HH:MM:SS"
                )
                return

        # Check attachment availability if selected
        attachment_path = ""
        if self.gui.chk_attachment_var.get():
            attachment_path = self.gui.attachment_file_path
            if not attachment_path or not os.path.exists(attachment_path):
                messagebox.showerror("Attachment Missing", "Please select a valid attachment file or disable attachments.")
                return

        # Clear campaign run state flags
        self.is_sending = True
        self.is_paused = False
        self.stop_requested = False
        
        # Lock send UI panels
        self.gui.set_sending_controls_state("sending")
        
        # Spin up campaign background thread
        self.campaign_thread = threading.Thread(
            target=self._execute_campaign_thread,
            args=(selected_leads, template_body, attachment_path, schedule_time),
            daemon=True
        )
        self.campaign_thread.start()

    def handle_pause_campaign(self) -> None:
        """Toggles execution thread between active and paused states."""
        if not self.is_sending:
            return
            
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.gui.set_sending_controls_state("paused")
            self.gui.append_log("Campaign paused by user.")
        else:
            self.gui.set_sending_controls_state("sending")
            self.gui.append_log("Campaign resumed.")

    def handle_stop_campaign(self) -> None:
        """Signals campaign thread loop to terminate."""
        if not self.is_sending:
            return
            
        if messagebox.askyesno("Confirm Stop", "Are you sure you want to stop the campaign? Any messages in progress will finish, and remaining will be skipped."):
            self.stop_requested = True
            self.is_paused = False  # break out of pause block if stuck in pause
            self.gui.append_log("Stopping campaign... Waiting for current send step to complete.")

    def _execute_campaign_thread(self, 
                                 selected_leads: List[Dict[str, Any]], 
                                 template_text: str, 
                                 attachment_path: str, 
                                 schedule_time: Optional[datetime]) -> None:
        """Runs the loop of sending API messages with placeholder replacement, delays, and retries."""
        total_count = len(selected_leads)
        sent_count = 0
        
        self.gui.append_log(f"Starting campaign targeting {total_count} leads.")
        
        # 1. Handle scheduling delay
        if schedule_time:
            self.gui.append_log(f"Campaign scheduled. Waiting until {schedule_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            while datetime.now() < schedule_time:
                if self.stop_requested:
                    self.gui.append_log("Scheduled campaign cancelled by user.")
                    self._end_campaign_run(sent_count, total_count, "Cancelled")
                    return
                    
                time_delta = schedule_time - datetime.now()
                hours, remainder = divmod(int(time_delta.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                countdown_str = f"Scheduled launch in: {hours:02d}:{minutes:02d}:{seconds:02d}"
                
                # Update progress text
                self.gui.update_progress(0, total_count, countdown_str)
                time.sleep(1)

        # 2. Upload media file once to Meta if media attachment is active
        media_id = ""
        if attachment_path:
            self.gui.append_log(f"Uploading media file to WhatsApp: {Path(attachment_path).name}...")
            self.gui.update_progress(0, total_count, "Uploading media attachment...")
            
            # Execute upload
            success, upload_id, err_msg = self.api_client.upload_media(attachment_path, retry_limit=self.settings.retry_limit)
            
            if success:
                media_id = upload_id
                self.gui.append_log(f"Media uploaded successfully. Reference ID: {media_id}")
            else:
                self.gui.append_log(f"Media Upload Failed: {err_msg}")
                messagebox.showerror("Media Upload Failed", f"Could not upload brochure file to Meta server:\n{err_msg}")
                self._end_campaign_run(0, total_count, "Upload Error")
                return

        # 3. Message dispatching loop
        for idx, lead in enumerate(selected_leads):
            # Check pause/resume state
            while self.is_paused and not self.stop_requested:
                time.sleep(0.5)

            # Check stop request
            if self.stop_requested:
                self.gui.append_log("Campaign interrupted by user.")
                break
                
            lead_name = lead["name"]
            raw_phone = lead["original_phone"]
            
            # Format number
            valid, phone_to_send = validate_and_format_phone(raw_phone)
            
            self.gui.append_log(f"[{idx+1}/{total_count}] Processing: {lead_name} ({phone_to_send or raw_phone})...")
            self.gui.update_progress(idx, total_count, f"Sending message {idx+1} of {total_count}...")
            
            # Update state in lead rows
            lead["status"] = "Queued"
            self.gui.display_leads_table(self.gui.leads_data)
            
            if not valid:
                err_msg = f"Skipped: Phone number '{raw_phone}' is invalid."
                self.gui.append_log(err_msg)
                lead["status"] = "Failed"
                lead["validation_error"] = "Invalid phone number."
                self.logger.log_transmission(lead_name, raw_phone, "", "Failed", error_msg=err_msg)
                self.gui.display_leads_table(self.gui.leads_data)
                self.refresh_dashboard_stats()
                continue

            # Process template body placeholders
            personalized_msg = self.tpl_manager.replace_placeholders(template_text, lead)
            
            # Initialize send results variables
            api_success = False
            wamid = ""
            response_data = {}
            
            # Try to send
            try:
                # If media attachment is active
                if media_id:
                    # Caption length validation: if custom text fits caption limit (1024), send it in a single API hit.
                    if len(personalized_msg) <= 1024:
                        api_success, wamid, response_data = self.api_client.send_media_message(
                            to_phone=phone_to_send,
                            media_id=media_id,
                            file_path=attachment_path,
                            caption=personalized_msg,
                            retry_limit=self.settings.retry_limit
                        )
                    else:
                        # Personalized message exceeds 1024 characters.
                        # Meta doesn't support caption > 1024. Send media first, then send text message separately.
                        self.gui.append_log("Message text > 1024 characters. Sending media first, then text separately...")
                        
                        media_success, media_wamid, media_response = self.api_client.send_media_message(
                            to_phone=phone_to_send,
                            media_id=media_id,
                            file_path=attachment_path,
                            caption="",
                            retry_limit=self.settings.retry_limit
                        )
                        
                        if media_success:
                            # Send personalized text separately
                            time.sleep(1) # short rest
                            api_success, wamid, response_data = self.api_client.send_text_message(
                                to_phone=phone_to_send,
                                text=personalized_msg,
                                retry_limit=self.settings.retry_limit
                            )
                        else:
                            api_success = False
                            wamid = media_wamid
                            response_data = media_response
                else:
                    # Text only send
                    api_success, wamid, response_data = self.api_client.send_text_message(
                        to_phone=phone_to_send,
                        text=personalized_msg,
                        retry_limit=self.settings.retry_limit
                    )
                    
            except Exception as e:
                api_success = False
                wamid = "error"
                response_data = {"error": str(e)}
                
            # Handle transmission outcome
            if api_success:
                lead["status"] = "Sent"
                self.gui.append_log(f"Successfully sent message to {lead_name}. ID: {wamid}")
                self.logger.log_transmission(lead_name, phone_to_send, personalized_msg, "Sent", whatsapp_id=wamid)
                sent_count += 1
            else:
                lead["status"] = "Failed"
                err_text = response_data.get("error", {}).get("message", "API request failed.") if isinstance(response_data, dict) else str(response_data)
                lead["validation_error"] = err_text
                self.gui.append_log(f"Failed sending to {lead_name}: {err_text}")
                self.logger.log_transmission(lead_name, phone_to_send, personalized_msg, "Failed", error_msg=err_text)
                
            # Update GUI states dynamically
            self.gui.display_leads_table(self.gui.leads_data)
            self.refresh_dashboard_stats()
            
            # Auto-save campaign progress to Excel backup
            self.auto_save_campaign_progress()
            
            # Apply delay between sends (safely check for stops/pauses during sleep)
            if idx < total_count - 1:
                delay = self.settings.sender_delay
                for _ in range(delay * 10):
                    if self.stop_requested:
                        break
                    while self.is_paused and not self.stop_requested:
                        time.sleep(0.1)
                    time.sleep(0.1)
                    
        # Wrap up campaign run
        self._end_campaign_run(sent_count, total_count)

    def auto_save_campaign_progress(self) -> None:
        """Exports the active state of all leads to Excel progress backup report."""
        try:
            backup_path = self.base_dir / "reports" / "active_campaign_progress.xlsx"
            ExcelReader.export_report(self.gui.leads_data, str(backup_path))
        except Exception as e:
            # Silent logging to prevent console log spam
            pass

    def _end_campaign_run(self, sent: int, total: int, status: str = "Finished") -> None:
        """Re-enables GUI panels, logs final outcomes, and triggers completion alerts."""
        self.is_sending = False
        self.is_paused = False
        self.stop_requested = False
        
        self.gui.set_sending_controls_state("idle")
        self.gui.update_progress(sent, total, f"Campaign completed. Sent: {sent} | Failed: {total - sent}")
        
        self.gui.append_log(f"=== Campaign Completed ===")
        self.gui.append_log(f"Total Sent: {sent} | Total Failed: {total - sent}")
        self.gui.append_log(f"Progress report auto-saved to reports/active_campaign_progress.xlsx")
        
        # Trigger sound notification
        if self.settings.play_sound:
            play_notification_sound()
            
        messagebox.showinfo("Campaign Completed", f"Successfully dispatched {sent} of {total} messages.")

    def run(self) -> None:
        """Launches Tkinter main loop."""
        self.gui.mainloop()

if __name__ == "__main__":
    # Create required app assets/directories on boot
    Path("assets").mkdir(exist_ok=True)
    Path("templates").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)
    
    app = WhatsAppCampaignController()
    app.run()
