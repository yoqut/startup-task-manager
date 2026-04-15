"""
Thin re-export shim — all implementations live in core.sender.Sender.
Import from here for backward compatibility, or use Sender directly.
"""
from core.sender import Sender

__all__ = [
    "Sender",
    "send_html", "edit_html",
    "format_task", "format_report", "format_statistics", "format_department_summary",
    "paginate", "get_db_user", "require_role",
]

# Module-level aliases so existing `from telegram.utils import send_html` keeps working
send_html                = Sender.send_html
edit_html                = Sender.edit_html
format_task              = Sender.format_task
format_report            = Sender.format_report
format_statistics        = Sender.format_statistics
format_department_summary = Sender.format_department_summary
paginate                 = Sender.paginate
get_db_user              = Sender.get_db_user
require_role             = Sender.require_role
