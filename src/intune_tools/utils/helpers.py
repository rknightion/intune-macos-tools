"""Helper utilities for Intune Tools"""

from datetime import datetime
from typing import Optional, Any


def format_date(date_value: Any, format_str: str = "%Y-%m-%d %H:%M") -> str:
    """Format a date value to string"""
    if not date_value:
        return "N/A"

    if isinstance(date_value, str):
        try:
            date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        except:
            return date_value

    if isinstance(date_value, datetime):
        return date_value.strftime(format_str)

    return str(date_value)


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human readable format"""
    if not size_bytes or size_bytes == 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    index = 0
    size = float(size_bytes)

    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1

    return f"{size:.1f} {units[index]}"


def get_icon(app_type: str) -> str:
    """Get icon for app type"""
    icons = {
        'macOSLobApp': '📦',
        'macOSOfficeSuiteApp': '📄',
        'macOSMicrosoftEdgeApp': '🌐',
        'macOSMicrosoftDefenderApp': '🛡️',
        'macOSWebClip': '🔗',
        'macOSVppApp': '🛍️',
        'macOSPkgApp': '📦',
        'macOSDmgApp': '💿',
        'macOSMdmApp': '⚙️',
        'macOSCustomApp': '🔧'
    }
    return icons.get(app_type, '📱')


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def parse_version(version: str) -> tuple:
    """Parse version string to tuple for comparison"""
    if not version:
        return (0, 0, 0)

    try:
        parts = version.split('.')
        return tuple(int(p) for p in parts[:3])
    except:
        return (0, 0, 0)


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings
    Returns: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
    """
    v1 = parse_version(version1)
    v2 = parse_version(version2)

    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0