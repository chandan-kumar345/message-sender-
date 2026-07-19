import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class TemplateManager:
    """Manages the creation, loading, updating, deletion, and parsing of message templates saved in JSON."""
    
    def __init__(self, templates_dir: Path = None):
        if templates_dir is None:
            self.templates_dir = Path(__file__).resolve().parent / "templates"
        else:
            self.templates_dir = Path(templates_dir)
            
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.filepath = self.templates_dir / "templates.json"
        
        # Ensure the templates.json file exists
        if not self.filepath.exists():
            self._save_to_disk([])
            self._load_default_template()

    def _save_to_disk(self, data: List[Dict[str, str]]) -> None:
        """Saves templates list to templates.json."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write templates to disk: {e}")

    def load_templates(self) -> List[Dict[str, str]]:
        """Loads and returns all saved templates from templates.json."""
        try:
            if not self.filepath.exists():
                return []
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"JSON decode error reading {self.filepath}. Resetting file.")
            self._save_to_disk([])
            return []
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
            return []

    def _load_default_template(self) -> None:
        """Loads standard demo template when the file is first created."""
        default_body = (
            "Hello {{name}},\n\n"
            "Thank you for contacting Sooftcode.\n\n"
            "We provide:\n"
            "• Website Development\n"
            "• Android & iOS Apps\n"
            "• SEO\n"
            "• Digital Marketing\n"
            "• ERP & CRM Solutions\n\n"
            "Let us know how we can help you.\n\n"
            "Regards,\n"
            "Sooftcode Team"
        )
        self.save_template("Welcome Sooftcode", default_body)

    def save_template(self, name: str, body: str) -> Tuple[bool, str]:
        """Saves a new template or updates an existing one (based on name)."""
        name = name.strip()
        body = body.strip()
        
        if not name:
            return False, "Template name cannot be empty."
        if not body:
            return False, "Template body cannot be empty."
            
        templates = self.load_templates()
        
        # Check if template with the same name already exists
        for temp in templates:
            if temp["name"].lower() == name.lower():
                temp["body"] = body
                self._save_to_disk(templates)
                return True, f"Template '{name}' updated successfully."
                
        # If it doesn't exist, append new template
        templates.append({"name": name, "body": body})
        self._save_to_disk(templates)
        return True, f"Template '{name}' saved successfully."

    def delete_template(self, name: str) -> Tuple[bool, str]:
        """Deletes a template by name."""
        name = name.strip()
        templates = self.load_templates()
        
        filtered_templates = [t for t in templates if t["name"].lower() != name.lower()]
        
        if len(filtered_templates) == len(templates):
            return False, f"Template '{name}' not found."
            
        self._save_to_disk(filtered_templates)
        return True, f"Template '{name}' deleted successfully."

    @staticmethod
    def replace_placeholders(template_body: str, lead_data: Dict[str, Any]) -> str:
        """
        Replaces placeholders in the format {{placeholder}} with the lead's actual values.
        Placeholders supported:
            {{name}}
            {{company}}
            {{phone}}
            {{email}}
        """
        if not template_body:
            return ""
            
        text = template_body
        
        # Map fields (case-insensitive keys for flexibility)
        mappings = {
            "name": str(lead_data.get("name", "")),
            "company": str(lead_data.get("company", "")),
            "phone": str(lead_data.get("phone", "")),
            "email": str(lead_data.get("email", ""))
        }
        
        # Replace occurrences
        for key, value in mappings.items():
            # Matches {{key}} case-insensitively with potential spaces, e.g., {{ name }} or {{NAME}}
            pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", re.IGNORECASE)
            text = pattern.sub(value, text)
            
        return text
