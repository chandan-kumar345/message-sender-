import re
import platform
import logging

logger = logging.getLogger(__name__)

def clean_phone_number(phone: str) -> str:
    """Removes all non-digit characters from the phone number string."""
    if not phone:
        return ""
    # Cast to string and strip decimals if imported as float (e.g. 919876543210.0)
    phone_str = str(phone).strip()
    if phone_str.endswith(".0"):
        phone_str = phone_str[:-2]
    # Remove non-numeric characters
    cleaned = re.sub(r"\D", "", phone_str)
    return cleaned

def validate_and_format_phone(phone: str) -> tuple[bool, str]:
    """
    Validates and formats a phone number for the WhatsApp Business Cloud API.
    WhatsApp Cloud API expects numbers in the format: country code + phone number (digits only, no + or spaces).
    
    Special rule for Indian numbers:
    - If 10 digits and starts with 6-9, prepends '91'.
    - If 11 digits and starts with '0' followed by 6-9, strips '0' and prepends '91'.
    - If starts with '91' and has 12 digits, checks if it is a valid format.
    - If starts with '+91' or '0091', clean it and treat it as '91' + 10 digits.
    
    Returns:
        tuple[bool, str]: (is_valid, formatted_number)
    """
    cleaned = clean_phone_number(phone)
    if not cleaned:
        return False, ""
        
    # Check if it looks like an Indian number
    # Remove leading double zeros (e.g. 0091) or single zero if it is part of country code pattern
    if cleaned.startswith("0091") and len(cleaned) == 14:
        cleaned = cleaned[4:]
    elif cleaned.startswith("00") and len(cleaned) > 10:
        cleaned = cleaned[2:]
        
    # If the number starts with '91' and is 12 digits long
    if len(cleaned) == 12 and cleaned.startswith("91"):
        # The remaining 10 digits should match Indian mobile starting series (6-9)
        subscriber_part = cleaned[2:]
        if re.match(r"^[6-9]\d{9}$", subscriber_part):
            return True, cleaned
        else:
            return False, cleaned # Could be valid other country code, but flag if failed Indian check

    # Handle standard 10 digit Indian number
    if len(cleaned) == 10 and re.match(r"^[6-9]\d{9}$", cleaned):
        return True, "91" + cleaned

    # Handle 11 digits starting with 0 (Indian standard local code)
    if len(cleaned) == 11 and cleaned.startswith("0"):
        subscriber_part = cleaned[1:]
        if re.match(r"^[6-9]\d{9}$", subscriber_part):
            return True, "91" + subscriber_part

    # For other numbers, fallback to basic length check (7 to 15 digits is standard E.164 length)
    if 7 <= len(cleaned) <= 15:
        return True, cleaned

    return False, cleaned

def validate_email(email: str) -> bool:
    """Validates email format using regex."""
    if not email:
        return False
    email_str = str(email).strip()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email_str))

def play_notification_sound() -> None:
    """Plays standard system completion notification sound (cross-platform, optimized for Windows)."""
    try:
        if platform.system() == "Windows":
            import winsound
            # MB_ICONASTERISK represents a standard informational system sound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        else:
            # Fallback for macOS/Linux terminal beep
            print("\a", end="", flush=True)
    except Exception as e:
        logger.warning(f"Failed to play completion sound: {e}")
