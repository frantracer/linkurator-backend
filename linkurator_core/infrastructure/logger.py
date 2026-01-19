import logging

import logfire

from linkurator_core.infrastructure.config.settings import LogSettings


def configure_logging(
        settings: LogSettings,
) -> None:
    """
    Configures the logging settings for the application.
    """
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s: %(message)s",
        level=logging.getLevelNamesMapping()[settings.level.upper()],
        datefmt="%Y-%m-%d %H:%M:%S")

    if settings.logfire.enabled:
        logfire.configure(
            token=settings.logfire.token,
            scrubbing=False,
            environment=settings.logfire.environment,
            service_name="linkurator",
        )

        logfire.instrument_pydantic_ai()
