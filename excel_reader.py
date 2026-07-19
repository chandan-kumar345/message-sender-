import pandas as pd
from pathlib import Path
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple
import logging
from utils import validate_and_format_phone, validate_email

logger = logging.getLogger(__name__)

class ExcelReader:
    """Handles importing, parsing, validation, duplicate detection, and exporting of lead data from CSV/Excel."""

    # Standard column names expected by the application
    REQUIRED_COLS = ["name", "phone"]
    ALL_COLS = ["name", "phone", "email", "company", "status", "last_contact_date"]

    @staticmethod
    def detect_and_map_columns(columns: List[str]) -> Dict[str, str]:
        """
        Maps source file column names to standard application fields using regex/keywords.
        Returns a mapping dict: {source_column: standard_field}
        """
        mapping = {}
        
        # Rules for column detection
        patterns = {
            "name": re.compile(r"name|customer|lead|client", re.IGNORECASE),
            "phone": re.compile(r"phone|mobile|contact|number|tel", re.IGNORECASE),
            "email": re.compile(r"email|mail", re.IGNORECASE),
            "company": re.compile(r"company|organization|org|business|employer", re.IGNORECASE),
            "status": re.compile(r"status|state", re.IGNORECASE),
            "last_contact_date": re.compile(r"date|last contact|contact date|last_contact", re.IGNORECASE)
        }

        matched_standards = set()
        
        for col in columns:
            col_stripped = col.strip()
            # Try to match patterns
            matched = False
            for std_field, pattern in patterns.items():
                if std_field not in matched_standards and pattern.search(col_stripped):
                    mapping[col] = std_field
                    matched_standards.add(std_field)
                    matched = True
                    break
            
            # If no match but it's exactly named, enforce it
            if not matched:
                normalized = col_stripped.lower().replace(" ", "_")
                if normalized in patterns and normalized not in matched_standards:
                    mapping[col] = normalized
                    matched_standards.add(normalized)

        return mapping

    @classmethod
    def read_file(cls, file_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Reads an Excel or CSV file, detects columns, validates format, formats numbers,
        detects duplicates, and returns a list of dictionaries representing leads and a list of warnings/errors.
        
        Each dictionary contains:
        - name (str)
        - phone (str) - clean formatted E.164 number
        - original_phone (str) - original input string
        - email (str)
        - company (str)
        - status (str) - Pending, Sent, Failed, etc.
        - last_contact_date (str)
        - is_valid (bool)
        - validation_error (str)
        - is_duplicate (bool)
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # 1. Read data based on extension
        try:
            if path.suffix.lower() == ".csv":
                df = pd.read_csv(file_path)
            elif path.suffix.lower() in [".xlsx", ".xls"]:
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Unsupported file format. Please upload a .csv or .xlsx file.")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise ValueError(f"Could not parse file: {str(e)}")

        if df.empty:
            raise ValueError("The uploaded file is empty.")

        # Clean column names in df (remove spaces around headers)
        df.columns = [str(c).strip() for c in df.columns]

        # 2. Map columns
        col_mapping = cls.detect_and_map_columns(df.columns)
        
        # Verify required columns are present
        mapped_values = list(col_mapping.values())
        missing = [req for req in cls.REQUIRED_COLS if req not in mapped_values]
        if missing:
            raise ValueError(f"Missing required columns in file: {', '.join(missing)}. "
                             f"Please ensure you have columns mapping to: Name and Phone Number.")

        # Rename columns to standard names
        df_mapped = df.rename(columns=col_mapping)
        
        # Drop columns that are not mapped/needed to keep structure clean
        keep_cols = [col for col in df_mapped.columns if col in cls.ALL_COLS]
        df_standard = df_mapped[keep_cols].copy()

        # Add missing optional columns with default values
        for col in cls.ALL_COLS:
            if col not in df_standard.columns:
                if col == "status":
                    df_standard["status"] = "Pending"
                elif col == "last_contact_date":
                    df_standard["last_contact_date"] = ""
                else:
                    df_standard[col] = ""

        # Make sure NaN values are converted to appropriate empty types
        df_standard = df_standard.fillna("")

        leads: List[Dict[str, Any]] = []
        seen_phones = set()
        warnings = []

        for idx, row in df_standard.iterrows():
            lead_name = str(row["name"]).strip()
            raw_phone = str(row["phone"]).strip()
            email = str(row["email"]).strip()
            company = str(row["company"]).strip()
            status = str(row["status"]).strip()
            if not status:
                status = "Pending"
                
            last_contact = str(row["last_contact_date"]).strip()

            # Perform parsing of date if possible, otherwise keep string representation
            if last_contact:
                try:
                    # Try parsing pandas timestamp or datetime strings
                    if isinstance(row["last_contact_date"], (pd.Timestamp, datetime)):
                        last_contact = row["last_contact_date"].strftime("%Y-%m-%d")
                    else:
                        # Simple convert
                        parsed_dt = pd.to_datetime(last_contact)
                        last_contact = parsed_dt.strftime("%Y-%m-%d")
                except Exception:
                    # Fallback to whatever string was written
                    pass

            is_valid = True
            validation_error = ""
            is_duplicate = False

            # Validate name
            if not lead_name:
                is_valid = False
                validation_error = "Name cannot be empty."

            # Validate phone number
            formatted_phone = ""
            if is_valid:
                phone_valid, formatted_phone = validate_and_format_phone(raw_phone)
                if not phone_valid:
                    is_valid = False
                    validation_error = f"Invalid phone format: {raw_phone}."

            # Email validation (optional warning, doesn't invalidate lead, but logs a warning)
            if email and not validate_email(email):
                warnings.append(f"Row {idx+2}: Email address '{email}' is invalid.")

            # Duplicate check (only on valid formatted phones)
            if is_valid:
                if formatted_phone in seen_phones:
                    is_duplicate = True
                    validation_error = "Duplicate phone number."
                else:
                    seen_phones.add(formatted_phone)

            leads.append({
                "name": lead_name,
                "phone": formatted_phone if is_valid else raw_phone,
                "original_phone": raw_phone,
                "email": email,
                "company": company,
                "status": status,
                "last_contact_date": last_contact,
                "is_valid": is_valid and not is_duplicate,
                "validation_error": validation_error,
                "is_duplicate": is_duplicate
            })

        return leads, warnings

    @staticmethod
    def export_report(leads: List[Dict[str, Any]], export_path: str, filter_status: str = None) -> None:
        """
        Exports leads list to an Excel file. Can optionally filter by status (e.g. Sent, Failed).
        """
        export_leads = leads
        if filter_status:
            export_leads = [l for l in leads if l["status"].lower() == filter_status.lower()]

        if not export_leads:
            raise ValueError(f"No leads found to export with status: {filter_status or 'All'}")

        # Convert to Pandas DataFrame for export
        df = pd.DataFrame(export_leads)
        
        # Clean up dataframe columns for standard reporting
        column_mapping = {
            "name": "Lead Name",
            "phone": "Formatted Phone Number",
            "original_phone": "Original Phone Number",
            "email": "Email Address",
            "company": "Company",
            "status": "Delivery Status",
            "last_contact_date": "Last Contact Date",
            "validation_error": "Remarks / Errors"
        }
        
        # Rename and keep standard columns
        df_export = df.rename(columns=column_mapping)
        cols_to_keep = [v for k, v in column_mapping.items() if k in df.columns]
        df_export = df_export[cols_to_keep]

        # Save to Excel
        path = Path(export_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        df_export.to_excel(export_path, index=False, sheet_name="Leads Report")
        logger.info(f"Successfully exported {len(df_export)} rows to {export_path}")
