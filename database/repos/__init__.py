import logging

logger = logging.getLogger(__name__)

_USER_ID_WARNED = False

_WARN_USER_ID_MSG = (
    "Using default user_id=1. No authentication is implemented — "
    "all users share the same data. Set PATHWISE_ADMIN_PASSWORD for admin access."
)


def warn_default_user():
    global _USER_ID_WARNED
    if not _USER_ID_WARNED:
        _USER_ID_WARNED = True
        logger.warning(_WARN_USER_ID_MSG)
