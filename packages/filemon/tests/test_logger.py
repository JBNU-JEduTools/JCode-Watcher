import logging
from logging.handlers import RotatingFileHandler

from app.config.settings import settings
from app.utils.logger import APP_LOGGER_NAME, setup_logging


def test_filemon_file_logging_has_bounded_rotation(tmp_path):
    assert settings.LOG_BACKUP_COUNT == 5
    setup_logging(
        log_file_path=str(tmp_path),
        log_level="INFO",
        max_bytes=1024,
        backup_count=settings.LOG_BACKUP_COUNT,
    )
    logger = logging.getLogger(APP_LOGGER_NAME)
    file_handler = next(
        handler for handler in logger.handlers if isinstance(handler, RotatingFileHandler)
    )
    assert file_handler.maxBytes == 1024
    assert file_handler.backupCount == 5

    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
