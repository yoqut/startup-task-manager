"""
Handler registry — importing this package registers all bot handlers
against the AsyncTeleBot instance in telegram.loader.

Import order matters: state-specific handlers must be registered before
general text handlers so pyTelegramBotAPI matches the more-specific ones first.
"""

# 1. Commands (/start, /help, /cancel, back_to_main, noop)
from telegram.handlers import commands  # noqa: F401

# 2. Task management (state handlers + menu handlers)
from telegram.handlers import tasks  # noqa: F401

# 3. Report submission & review
from telegram.handlers import reports  # noqa: F401

# 4. Admin utilities (stats, users, broadcast)
from telegram.handlers import admin  # noqa: F401
