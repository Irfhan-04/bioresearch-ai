"""
Data Formatting Utilities
Convert, format, and transform data for API responses and exports
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import phonenumbers
from email_validator import EmailNotValidError, validate_email


class DataFormatter:
    """
    Utilities for formatting and transforming data
    """

    @staticmethod
    def format_datetime(dt: Optional[datetime], format: str = "iso") -> Optional[str]:
        """
        Format datetime to string

        Args:
            dt: Datetime object
            format: Output format ('iso', 'date', 'time', 'human')

        Returns:
            Formatted string or None
        """
        if dt is None:
            return None

        if format == "iso":
            return dt.isoformat()
        elif format == "date":
            return dt.strftime("%Y-%m-%d")
        elif format == "time":
            return dt.strftime("%H:%M:%S")
        elif format == "human":
            return dt.strftime("%B %d, %Y at %I:%M %p")
        elif format == "short":
            return dt.strftime("%Y-%m-%d %H:%M")
        else:
            return dt.isoformat()

    @staticmethod
    def format_uuid(uuid_obj: Optional[Union[UUID, str]]) -> Optional[str]:
        """
        Format UUID to string

        Args:
            uuid_obj: UUID object or string

        Returns:
            UUID string or None
        """
        if uuid_obj is None:
            return None

        if isinstance(uuid_obj, UUID):
            return str(uuid_obj)
        return str(uuid_obj)

    @staticmethod
    def format_email(email: Optional[str]) -> Optional[str]:
        """
        Format and normalize email address

        Args:
            email: Email string

        Returns:
            Normalized email or None
        """
        if not email:
            return None

        try:
            # Validate and normalize
            validated = validate_email(email, check_deliverability=False)
            return validated.normalized.lower()
        except EmailNotValidError:
            return email.lower().strip()

    @staticmethod
    def format_phone(
        phone: Optional[str], region: str = "US", format: str = "international"
    ) -> Optional[str]:
        """
        Format phone number

        Args:
            phone: Phone number string
            region: Default region code
            format: Output format ('international', 'national', 'e164')

        Returns:
            Formatted phone or None
        """
        if not phone:
            return None

        try:
            parsed = phonenumbers.parse(phone, region)

            if not phonenumbers.is_valid_number(parsed):
                return phone

            if format == "international":
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )
            elif format == "national":
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.NATIONAL
                )
            elif format == "e164":
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
            else:
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )
        except Exception:
            return phone

    @staticmethod
    def format_currency(
        amount: Optional[float], currency: str = "USD", decimal_places: int = 2
    ) -> Optional[str]:
        """
        Format currency amount

        Args:
            amount: Amount to format
            currency: Currency code
            decimal_places: Number of decimal places

        Returns:
            Formatted currency string
        """
        if amount is None:
            return None

        symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
        }

        symbol = symbols.get(currency, currency + " ")
        formatted = f"{amount:,.{decimal_places}f}"

        return f"{symbol}{formatted}"

    @staticmethod
    def format_percentage(
        value: Optional[float], decimal_places: int = 1
    ) -> Optional[str]:
        """
        Format percentage

        Args:
            value: Percentage value (0-100)
            decimal_places: Decimal places

        Returns:
            Formatted percentage string
        """
        if value is None:
            return None

        return f"{value:.{decimal_places}f}%"

    @staticmethod
    def format_number(
        value: Optional[Union[int, float]],
        decimal_places: Optional[int] = None,
        use_commas: bool = True,
    ) -> Optional[str]:
        """
        Format number with thousands separators

        Args:
            value: Number to format
            decimal_places: Decimal places (None for auto)
            use_commas: Use thousand separators

        Returns:
            Formatted number string
        """
        if value is None:
            return None

        if decimal_places is not None:
            formatted = f"{value:.{decimal_places}f}"
        else:
            formatted = str(value)

        if use_commas:
            parts = formatted.split(".")
            parts[0] = "{:,}".format(int(parts[0]))
            return ".".join(parts)

        return formatted

    @staticmethod
    def format_file_size(bytes: Optional[int]) -> Optional[str]:
        """
        Format file size in human-readable format

        Args:
            bytes: Size in bytes

        Returns:
            Formatted size (e.g., "1.5 MB")
        """
        if bytes is None or bytes == 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"

    @staticmethod
    def format_duration(seconds: Optional[int]) -> Optional[str]:
        """
        Format duration in human-readable format

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration (e.g., "1h 30m")
        """
        if seconds is None or seconds == 0:
            return "0s"

        parts = []

        hours = seconds // 3600
        if hours > 0:
            parts.append(f"{hours}h")
            seconds %= 3600

        minutes = seconds // 60
        if minutes > 0:
            parts.append(f"{minutes}m")
            seconds %= 60

        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")

        return " ".join(parts)

    @staticmethod
    def format_list(
        items: Optional[List[Any]], separator: str = ", ", max_items: int = 5
    ) -> Optional[str]:
        """
        Format list as string

        Args:
            items: List of items
            separator: Separator string
            max_items: Maximum items to show

        Returns:
            Formatted string
        """
        if not items:
            return None

        if len(items) <= max_items:
            return separator.join(str(item) for item in items)
        else:
            shown = separator.join(str(item) for item in items[:max_items])
            remaining = len(items) - max_items
            return f"{shown} (+{remaining} more)"

    @staticmethod
    def truncate_text(
        text: Optional[str], max_length: int = 100, suffix: str = "..."
    ) -> Optional[str]:
        """
        Truncate text to maximum length

        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix for truncated text

        Returns:
            Truncated text
        """
        if not text or len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    @staticmethod
    def format_score(score: Optional[int], max_score: int = 100) -> Optional[str]:
        """
        Format propensity score with visual indicator

        Args:
            score: Score value
            max_score: Maximum possible score

        Returns:
            Formatted score string
        """
        if score is None:
            return None

        percentage = (score / max_score) * 100

        if percentage >= 80:
            indicator = "🟢"  # High
        elif percentage >= 50:
            indicator = "🟡"  # Medium
        else:
            indicator = "🔴"  # Low

        return f"{indicator} {score}/{max_score}"

    @staticmethod
    def format_name(
        first_name: Optional[str],
        last_name: Optional[str],
        title: Optional[str] = None,
    ) -> str:
        """
        Format person's name

        Args:
            first_name: First name
            last_name: Last name
            title: Title (Dr., Prof., etc.)

        Returns:
            Formatted full name
        """
        parts = []

        if title:
            parts.append(title)

        if first_name:
            parts.append(first_name)

        if last_name:
            parts.append(last_name)

        return " ".join(parts) if parts else "Unknown"

    @staticmethod
    def format_address(components: Dict[str, Optional[str]]) -> str:
        """
        Format address from components

        Args:
            components: Dict with street, city, state, zip, country

        Returns:
            Formatted address
        """
        parts = []

        if components.get("street"):
            parts.append(components["street"])

        city_state = []
        if components.get("city"):
            city_state.append(components["city"])
        if components.get("state"):
            city_state.append(components["state"])

        if city_state:
            parts.append(", ".join(city_state))

        if components.get("zip"):
            parts.append(components["zip"])

        if components.get("country"):
            parts.append(components["country"])

        return ", ".join(parts) if parts else ""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for safe storage

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        import re

        # Remove special characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "", filename)

        # Replace spaces with underscores
        sanitized = sanitized.replace(" ", "_")

        # Limit length
        if len(sanitized) > 200:
            name, ext = sanitized.rsplit(".", 1) if "." in sanitized else (sanitized, "")
            sanitized = name[:200 - len(ext) - 1] + "." + ext if ext else name[:200]

        return sanitized.lower()

    @staticmethod
    def format_dict_for_display(data: Dict[str, Any], indent: int = 2) -> str:
        """
        Format dictionary for human-readable display

        Args:
            data: Dictionary to format
            indent: Indentation spaces

        Returns:
            Formatted string
        """
        import json

        return json.dumps(data, indent=indent, default=str, ensure_ascii=False)


# Convenience functions
def format_lead_name(lead_data: Dict[str, Any]) -> str:
    """Format lead name with title"""
    return DataFormatter.format_name(
        first_name=lead_data.get("name", "").split()[0] if lead_data.get("name") else None,
        last_name=" ".join(lead_data.get("name", "").split()[1:]) if lead_data.get("name") and len(lead_data.get("name", "").split()) > 1 else None,
        title=lead_data.get("title"),
    )


def format_export_filename(format: str, timestamp: Optional[datetime] = None) -> str:
    """Generate export filename"""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    date_str = DataFormatter.format_datetime(timestamp, format="date")
    time_str = timestamp.strftime("%H%M%S")

    extensions = {
        "csv": "csv",
        "excel": "xlsx",
        "json": "json",
        "pdf": "pdf",
    }

    ext = extensions.get(format, "csv")
    filename = f"leads_export_{date_str}_{time_str}.{ext}"

    return DataFormatter.sanitize_filename(filename)


# Export all
__all__ = [
    "DataFormatter",
    "format_lead_name",
    "format_export_filename",
]