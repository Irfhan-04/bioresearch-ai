"""
Data Validation Utilities
Custom validators for API inputs and data integrity
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
from uuid import UUID

import phonenumbers
from email_validator import EmailNotValidError, validate_email
from pydantic import ValidationError


class ValidationError(Exception):
    """Custom validation error"""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class DataValidator:
    """
    Comprehensive data validation utilities
    """

    @staticmethod
    def validate_email(email: str, check_deliverability: bool = False) -> tuple[bool, Optional[str]]:
        """
        Validate email address

        Args:
            email: Email to validate
            check_deliverability: Check if domain accepts email

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"

        try:
            validated = validate_email(email, check_deliverability=check_deliverability)
            return True, None
        except EmailNotValidError as e:
            return False, str(e)

    @staticmethod
    def validate_phone(phone: str, region: str = "US") -> tuple[bool, Optional[str]]:
        """
        Validate phone number

        Args:
            phone: Phone number to validate
            region: Default region code

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not phone:
            return False, "Phone number is required"

        try:
            parsed = phonenumbers.parse(phone, region)

            if not phonenumbers.is_valid_number(parsed):
                return False, "Invalid phone number"

            return True, None
        except Exception as e:
            return False, f"Invalid phone number: {str(e)}"

    @staticmethod
    def validate_url(url: str, schemes: Optional[List[str]] = None) -> tuple[bool, Optional[str]]:
        """
        Validate URL

        Args:
            url: URL to validate
            schemes: Allowed schemes (default: ['http', 'https'])

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL is required"

        allowed_schemes = schemes or ["http", "https"]

        try:
            parsed = urlparse(url)

            if not parsed.scheme:
                return False, "URL must include scheme (http:// or https://)"

            if parsed.scheme not in allowed_schemes:
                return False, f"URL scheme must be one of: {', '.join(allowed_schemes)}"

            if not parsed.netloc:
                return False, "Invalid URL format"

            return True, None
        except Exception as e:
            return False, f"Invalid URL: {str(e)}"

    @staticmethod
    def validate_uuid(value: str) -> tuple[bool, Optional[str]]:
        """
        Validate UUID

        Args:
            value: UUID string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "UUID is required"

        try:
            UUID(value)
            return True, None
        except ValueError:
            return False, "Invalid UUID format"

    @staticmethod
    def validate_password(password: str, min_length: int = 8) -> tuple[bool, List[str]]:
        """
        Validate password strength

        Args:
            password: Password to validate
            min_length: Minimum length

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if not password:
            return False, ["Password is required"]

        if len(password) < min_length:
            errors.append(f"Password must be at least {min_length} characters")

        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            errors.append("Password must contain at least one special character")

        return len(errors) == 0, errors

    @staticmethod
    def validate_date_range(
        start_date: datetime, end_date: datetime
    ) -> tuple[bool, Optional[str]]:
        """
        Validate date range

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not start_date or not end_date:
            return False, "Both start and end dates are required"

        if start_date > end_date:
            return False, "Start date must be before end date"

        # Check if range is too large (optional)
        max_days = 365
        if (end_date - start_date).days > max_days:
            return False, f"Date range cannot exceed {max_days} days"

        return True, None

    @staticmethod
    def validate_score(score: int, min_score: int = 0, max_score: int = 100) -> tuple[bool, Optional[str]]:
        """
        Validate score value

        Args:
            score: Score to validate
            min_score: Minimum allowed score
            max_score: Maximum allowed score

        Returns:
            Tuple of (is_valid, error_message)
        """
        if score is None:
            return False, "Score is required"

        if not isinstance(score, int):
            return False, "Score must be an integer"

        if score < min_score or score > max_score:
            return False, f"Score must be between {min_score} and {max_score}"

        return True, None

    @staticmethod
    def validate_subscription_tier(tier: str) -> tuple[bool, Optional[str]]:
        """
        Validate subscription tier

        Args:
            tier: Tier name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_tiers = ["free", "pro", "team", "enterprise"]

        if not tier:
            return False, "Subscription tier is required"

        if tier.lower() not in valid_tiers:
            return False, f"Tier must be one of: {', '.join(valid_tiers)}"

        return True, None

    @staticmethod
    def validate_priority_tier(tier: str) -> tuple[bool, Optional[str]]:
        """
        Validate priority tier

        Args:
            tier: Priority tier to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_tiers = ["HIGH", "MEDIUM", "LOW"]

        if not tier:
            return False, "Priority tier is required"

        if tier.upper() not in valid_tiers:
            return False, f"Priority tier must be one of: {', '.join(valid_tiers)}"

        return True, None

    @staticmethod
    def validate_export_format(format: str) -> tuple[bool, Optional[str]]:
        """
        Validate export format

        Args:
            format: Export format to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_formats = ["csv", "excel", "json", "pdf"]

        if not format:
            return False, "Export format is required"

        if format.lower() not in valid_formats:
            return False, f"Format must be one of: {', '.join(valid_formats)}"

        return True, None

    @staticmethod
    def validate_search_type(search_type: str) -> tuple[bool, Optional[str]]:
        """
        Validate search type

        Args:
            search_type: Search type to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_types = ["pubmed", "linkedin", "conference", "funding", "custom"]

        if not search_type:
            return False, "Search type is required"

        if search_type.lower() not in valid_types:
            return False, f"Search type must be one of: {', '.join(valid_types)}"

        return True, None

    @staticmethod
    def validate_pagination(page: int, size: int, max_size: int = 100) -> tuple[bool, Optional[str]]:
        """
        Validate pagination parameters

        Args:
            page: Page number
            size: Page size
            max_size: Maximum page size

        Returns:
            Tuple of (is_valid, error_message)
        """
        if page < 1:
            return False, "Page must be 1 or greater"

        if size < 1:
            return False, "Size must be 1 or greater"

        if size > max_size:
            return False, f"Size cannot exceed {max_size}"

        return True, None

    @staticmethod
    def validate_sort_params(
        sort_by: str, sort_order: str, allowed_fields: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate sort parameters

        Args:
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            allowed_fields: List of allowed sort fields

        Returns:
            Tuple of (is_valid, error_message)
        """
        if sort_by not in allowed_fields:
            return False, f"sort_by must be one of: {', '.join(allowed_fields)}"

        if sort_order.lower() not in ["asc", "desc"]:
            return False, "sort_order must be 'asc' or 'desc'"

        return True, None

    @staticmethod
    def validate_tags(tags: List[str], max_tags: int = 20, max_length: int = 50) -> tuple[bool, Optional[str]]:
        """
        Validate tags list

        Args:
            tags: List of tags
            max_tags: Maximum number of tags
            max_length: Maximum tag length

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not tags:
            return True, None  # Empty tags list is valid

        if len(tags) > max_tags:
            return False, f"Maximum {max_tags} tags allowed"

        for tag in tags:
            if len(tag) > max_length:
                return False, f"Tag length cannot exceed {max_length} characters"

            if not re.match(r'^[a-zA-Z0-9\-_]+$', tag):
                return False, "Tags can only contain letters, numbers, hyphens, and underscores"

        return True, None

    @staticmethod
    def validate_json_field(data: Union[Dict, List], required_keys: Optional[List[str]] = None) -> tuple[bool, Optional[str]]:
        """
        Validate JSON field

        Args:
            data: JSON data to validate
            required_keys: Required keys if dict

        Returns:
            Tuple of (is_valid, error_message)
        """
        if data is None:
            return False, "JSON data is required"

        if isinstance(data, dict) and required_keys:
            missing_keys = [key for key in required_keys if key not in data]
            if missing_keys:
                return False, f"Missing required keys: {', '.join(missing_keys)}"

        return True, None

    @staticmethod
    def validate_file_upload(
        filename: str, max_size_mb: int = 10, allowed_extensions: Optional[List[str]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate file upload

        Args:
            filename: Name of uploaded file
            max_size_mb: Maximum file size in MB
            allowed_extensions: List of allowed file extensions

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not filename:
            return False, "Filename is required"

        # Check extension
        if allowed_extensions:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in allowed_extensions:
                return False, f"File type must be one of: {', '.join(allowed_extensions)}"

        # Check for malicious patterns
        dangerous_patterns = ["../", "..\\", "<script>", "<?php"]
        if any(pattern in filename.lower() for pattern in dangerous_patterns):
            return False, "Filename contains potentially dangerous characters"

        return True, None

    @staticmethod
    def validate_cron_expression(cron: str) -> tuple[bool, Optional[str]]:
        """
        Validate cron expression (basic validation)

        Args:
            cron: Cron expression to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not cron:
            return False, "Cron expression is required"

        parts = cron.split()

        if len(parts) != 5:
            return False, "Cron expression must have 5 parts (minute hour day month weekday)"

        # Basic validation of each part
        for i, part in enumerate(parts):
            if part != "*" and not re.match(r'^(\d+|\d+-\d+|\*/\d+)$', part):
                field_names = ["minute", "hour", "day", "month", "weekday"]
                return False, f"Invalid {field_names[i]} format in cron expression"

        return True, None


def validate_lead_data(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate lead creation/update data

    Args:
        data: Lead data dictionary

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Required field: name
    if not data.get("name"):
        errors.append("Name is required")
    elif len(data["name"]) > 255:
        errors.append("Name cannot exceed 255 characters")

    # Email validation (optional but must be valid if provided)
    if data.get("email"):
        is_valid, error = DataValidator.validate_email(data["email"])
        if not is_valid:
            errors.append(error)

    # Phone validation (optional)
    if data.get("phone"):
        is_valid, error = DataValidator.validate_phone(data["phone"])
        if not is_valid:
            errors.append(error)

    # LinkedIn URL validation (optional)
    if data.get("linkedin_url"):
        is_valid, error = DataValidator.validate_url(data["linkedin_url"])
        if not is_valid:
            errors.append(error)

    # Score validation (optional)
    if data.get("propensity_score") is not None:
        is_valid, error = DataValidator.validate_score(data["propensity_score"])
        if not is_valid:
            errors.append(error)

    # Tags validation (optional)
    if data.get("tags"):
        is_valid, error = DataValidator.validate_tags(data["tags"])
        if not is_valid:
            errors.append(error)

    return len(errors) == 0, errors


def validate_pipeline_config(config: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate pipeline configuration

    Args:
        config: Pipeline configuration dictionary

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Required: search_queries
    if "search_queries" not in config:
        errors.append("search_queries is required")
    elif not config["search_queries"]:
        errors.append("At least one search query is required")
    else:
        for i, query in enumerate(config["search_queries"]):
            if "query" not in query:
                errors.append(f"Query #{i+1}: 'query' field is required")
            if "source" not in query:
                errors.append(f"Query #{i+1}: 'source' field is required")

    # Validate filters (optional)
    if "filters" in config:
        filters = config["filters"]
        if "min_score" in filters:
            is_valid, error = DataValidator.validate_score(filters["min_score"])
            if not is_valid:
                errors.append(f"filters.min_score: {error}")

    return len(errors) == 0, errors


# Export all
__all__ = [
    "ValidationError",
    "DataValidator",
    "validate_lead_data",
    "validate_pipeline_config",
]