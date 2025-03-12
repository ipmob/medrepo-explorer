import time
import functools
from typing import Any, Callable, TypeVar, cast

from app.utils.logger import logger

F = TypeVar('F', bound=Callable[..., Any])

def timing_decorator(func: F) -> F:
    """
    Decorator that logs the execution time of a function.
    
    Args:
        func: The function to time
        
    Returns:
        The wrapped function that logs timing information
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        logger.info(f"{func.__name__} completed in {execution_time:.4f} seconds")
        return result
    
    return cast(F, wrapper) 