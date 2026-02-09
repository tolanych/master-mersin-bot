import re

def normalize_phone(phone: str) -> str:
    """
    Formalize phone number:
    1. Remove all characters except digits and the first '+' (if it's at the start).
    2. For Turkish numbers, ensure they are in +90XXXXXXXXXX format.
    """
    if not phone:
        return ""
    
    # Remove all non-digits except initial +
    phone = phone.strip()
    has_initial_plus = phone.startswith('+')
    
    # Extract only digits
    digits = re.sub(r'\D', '', phone)
    if not digits:
        return ""

    # Turkish normalization:
    # 5xxxxxxxxx (10) | 05xxxxxxxxx (11) | 905xxxxxxxxx (12) -> +905xxxxxxxxx
    if len(digits) == 10 and digits.startswith('5'):
        return f"+90{digits}"
    elif len(digits) == 11 and digits.startswith('05'):
        return f"+90{digits[1:]}"
    elif len(digits) == 12 and digits.startswith('905'):
        return f"+{digits}"
    elif len(digits) == 13 and digits.startswith('905'):
        return f"+{digits[1:]}" # Case for 090...

    # Russian normalization:
    # 79xxxxxxxxx (11) | 89xxxxxxxxx (11, local) -> +79xxxxxxxxx
    if len(digits) == 11:
        if digits.startswith('7'):
            return f"+{digits}"
        if digits.startswith('8'):
            return f"+7{digits[1:]}"

    # Generic normalization for other international numbers
    # If length >= 10 and doesn't have a plus, but looks like it should (doesn't start with 0)
    if not has_initial_plus and len(digits) >= 10 and not digits.startswith('0'):
        return f"+{digits}"
    
    if has_initial_plus:
        return f"+{digits}"
        
    return digits

def is_valid_phone(phone: str) -> bool:
    """
    Validates phone number.
    If it starts with +9 (likely Turkish), applies strict 7-15 digits check.
    Otherwise, allows more flexible digit count.
    """
    if not phone:
        return False
    
    phone = phone.strip()
    # General allowed characters check
    if not re.fullmatch(r"[0-9+()\-\s]{5,30}", phone):
        return False
        
    digits = re.sub(r"\D", "", phone)
    
    # If it starts with +9 (Turkish context) OR it's a local Turkish format (starts with 5, 05, 90)
    # Actually, the user specifically mentioned "+9"
    if phone.startswith('+9') or (not phone.startswith('+') and (phone.startswith('5') or phone.startswith('05') or phone.startswith('90'))):
        return 7 <= len(digits) <= 15
    
    # For others (e.g. +7, +1, etc.), we are more lenient
    return len(digits) >= 5

def get_phone_search_variants(phone: str) -> list[str]:
    """
    Returns a list of possible representations of the phone number in the database
    to ensure we find duplicates even if they were stored in different formats.
    """
    normalized = normalize_phone(phone)
    if not normalized:
        return []
    
    variants = {normalized}
    
    # If it's a Turkish number (+905...), also check 05... and 5...
    if normalized.startswith('+905') and len(normalized) == 13:
        ten_digits = normalized[3:] # 5xxxxxxxxx
        variants.add(f"0{ten_digits}")
        variants.add(ten_digits)
    
    return list(variants)
