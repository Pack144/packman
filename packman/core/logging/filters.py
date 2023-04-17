import logging
from logging import LogRecord

from packman.core.exceptions import SpamDetected


class ExcludeSpamDetected(logging.Filter):
    def filter(self, record: LogRecord) -> bool:
        if record.exc_info:
            exc_type, exc_value = record.exc_info[:2]
            if isinstance(exc_value, SpamDetected):
                return False
        return True
