import backoff

from devworkwire.shared.global_variables import MAX_ERROR_RETRIES
from devworkwire.shared.log_config import get_logger

log = get_logger(__name__)


def retry_on_exception(max_tries=MAX_ERROR_RETRIES):
    """
    Reusable decorator for retrying a function with backoff on exceptions.

    Args:
        max_tries (int): Maximum number of attempts before giving up.

    Returns:
        callable: A decorator function wrapping the retry logic.
    """
    return backoff.on_exception(
        backoff.expo,  # Exponential backoff
        Exception,  # Retry on any exception
        max_tries=max_tries,  # Maximum number of attempts
        on_backoff=lambda details: log.warning(
            f"Retrying due to: {details['exception']}"
        ),
        on_giveup=lambda details: log.error(
            f"Giving up after {details['tries']} attempts."
        ),
    )
