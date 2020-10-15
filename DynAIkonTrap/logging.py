"""
Provides access to a preset Python logger. To use call `get_logger()` once at the start of the file with the parameter set to `__name__`. Doing so ensures the logging output displays which module a log message was generated in.

Example usage:
```python
logger = get_logger(__name__)

logger.error('A dreadful thing is happening')
```
"""
from logging import Logger, getLogger, StreamHandler, Formatter, DEBUG, INFO

LOG_LEVEL = DEBUG


def get_logger(name: str) -> Logger:
    """Creates a `Logger` instance with messages set to print the path according to `name`. The function should always be called with `__name__`

    Args:
        name (str): file path as given by `__name__`

    Returns:
        Logger: A `Logger` instance. Call the standard info, warning, error, etc. functions to generate
    """
    logger = getLogger(name)
    logger.setLevel(LOG_LEVEL)
    _ch = StreamHandler()
    _ch.setLevel(LOG_LEVEL)
    _ch.setFormatter(Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(_ch)
    return logger
