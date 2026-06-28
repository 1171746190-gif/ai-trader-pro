import hashlib
import logging
import re
import secrets
from typing import Optional

logger = logging.getLogger(__name__)

# ==================== Password Hashing ====================

def hash_password(password: str) -> str:
    """Hash password with SHA256 and salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    try:
        salt, hash_value = hashed.split("$")
        check = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
        return check == hash_value
    except (ValueError, AttributeError):
        return False


# ==================== Token Generation ====================

def generate_token(length: int = 43) -> str:
    """Generate secure random token."""
    return secrets.token_urlsafe(length)


# ==================== Wallet Address Validation ====================

def is_valid_wallet_address(address: str) -> bool:
    """Validate Ethereum wallet address."""
    if not address or not address.startswith("0x"):
        return False
    if len(address) != 42:
        return False
    try:
        int(address[2:], 16)
        return True
    except ValueError:
        return False


# ==================== Input Validation ====================

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol."""
    if not symbol or len(symbol) > 20:
        return False
    pattern = r'^[A-Za-z0-9\-./]+$'
    return bool(re.match(pattern, symbol))


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input."""
    if not text:
        return ""
    # Remove null bytes
    text = text.replace('\x00', '')
    # Trim whitespace
    text = text.strip()
    # Limit length
    return text[:max_length]


# ==================== Market Time Utilities ====================

def is_us_market_open() -> bool:
    """Check if US stock market is open."""
    from datetime import datetime, time, timezone, timedelta
    
    # US market hours: Mon-Fri 9:30-16:00 ET
    et = timezone(timedelta(hours=-5))
    now = datetime.now(et)
    
    # Check weekday
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check time
    market_open = time(9, 30)
    market_close = time(16, 0)
    current_time = now.time()
    
    return market_open <= current_time <= market_close


def get_next_market_open() -> Optional[str]:
    """Get next market open time."""
    from datetime import datetime, time, timezone, timedelta
    
    et = timezone(timedelta(hours=-5))
    now = datetime.now(et)
    
    # If weekend, move to next Monday
    days_ahead = 0
    if now.weekday() >= 5:  # Weekend
        days_ahead = 7 - now.weekday()
    elif now.time() >= time(16, 0):  # After market close
        days_ahead = 1
        if now.weekday() == 4:  # Friday after close
            days_ahead = 3
    
    next_open = now + timedelta(days=days_ahead)
    next_open = next_open.replace(hour=9, minute=30, second=0, microsecond=0)
    
    return next_open.isoformat()
