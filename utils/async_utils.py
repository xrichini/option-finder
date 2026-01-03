# utils/async_utils.py
import asyncio
import concurrent.futures
import functools
import nest_asyncio
from typing import Any, Coroutine, Callable, TypeVar, Optional
import warnings
import logging

# Apply nest_asyncio at module level
nest_asyncio.apply()

T = TypeVar("T")
logger = logging.getLogger(__name__)


def run_async_safely(coro: Coroutine[Any, Any, T], timeout: Optional[float] = 30) -> T:
    """
    Safely run an async coroutine in any environment.

    This function handles the complexity of running async code in environments
    that might already have an event loop running (like web frameworks).

    Args:
        coro: The coroutine to run
        timeout: Maximum time to wait for completion (seconds)

    Returns:
        The result of the coroutine

    Raises:
        asyncio.TimeoutError: If the operation times out
        RuntimeError: If there's an event loop issue
    """
    try:
        # First, try to get the current event loop
        loop = asyncio.get_event_loop()

        if loop.is_running():
            # If we're in a running loop (like in web frameworks), we need to be careful
            # We'll run the coroutine in a thread pool to avoid blocking
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=timeout)
        else:
            # If no loop is running, we can safely use asyncio.run
            return asyncio.run(coro)

    except RuntimeError as e:
        error_msg = str(e).lower()
        if (
            "already running" in error_msg
            or "cannot be called from a running event loop" in error_msg
        ):
            # Fallback: run in thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=timeout)
        else:
            raise
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Error running async operation: {str(e)}")
        raise


# For backward compatibility with Streamlit code
def run_async_in_streamlit(
    coro: Coroutine[Any, Any, T], timeout: Optional[float] = 30
) -> T:
    """Backward compatibility alias for run_async_safely"""
    return run_async_safely(coro, timeout)


def create_async_task_safe(
    coro: Coroutine, name: Optional[str] = None
) -> Optional[asyncio.Task]:
    """
    Safely create an asyncio task, handling event loop issues.

    Args:
        coro: The coroutine to create a task for
        name: Optional name for the task

    Returns:
        The created task, or None if it couldn't be created
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.create_task(coro, name=name)
        else:
            # If no loop is running, we can't create a task
            warnings.warn("No running event loop, cannot create task")
            return None
    except RuntimeError:
        warnings.warn("Could not create async task due to event loop issues")
        return None


def async_to_sync(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    Decorator to convert an async function to sync for use in any environment.

    Usage:
        @async_to_sync
        async def my_async_function(arg1, arg2):
            # async code here
            return result

        # Now can be called synchronously
        result = my_async_function(arg1, arg2)
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        coro = func(*args, **kwargs)
        return run_async_safely(coro)

    return wrapper


class AsyncContextManager:
    """
    Context manager to handle async resources safely in any environment.

    Usage:
        async with AsyncContextManager() as acm:
            client = AsyncTradierClient()
            acm.add_resource(client)
            # Use client...
            # Resources will be cleaned up automatically
    """

    def __init__(self):
        self.resources = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    def add_resource(self, resource):
        """Add a resource that has a close() method to be cleaned up"""
        self.resources.append(resource)

    async def cleanup(self):
        """Clean up all registered resources"""
        for resource in reversed(self.resources):  # Clean up in reverse order
            try:
                if hasattr(resource, "close"):
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()
            except Exception:
                logger.exception("Warning: Error cleaning up resource %s", resource)
        self.resources.clear()


def safe_async_run_with_fallback(
    async_func: Callable, sync_fallback: Callable, *args, **kwargs
):
    """
    Try to run an async function, fall back to sync version if event loop issues occur.

    Args:
        async_func: The async function to try first
        sync_fallback: The sync function to use as fallback
        *args, **kwargs: Arguments to pass to both functions

    Returns:
        Result from either async or sync function
    """
    try:
        if asyncio.iscoroutinefunction(async_func):
            coro = async_func(*args, **kwargs)
            return run_async_safely(coro)
        else:
            return async_func(*args, **kwargs)
    except (RuntimeError, asyncio.TimeoutError) as e:
        if "event loop" in str(e).lower() or "timeout" in str(e).lower():
            # Fall back to sync version
            return sync_fallback(*args, **kwargs)
        else:
            raise


def cleanup_async_resources(resources: list):
    """Clean up a list of async resources"""
    for resource in resources:
        try:
            # Try to close the resource
            if hasattr(resource, "close"):
                if asyncio.iscoroutinefunction(resource.close):
                    # Try to handle async cleanup safely
                    try:
                        # First try to get the event loop
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Try to create a task
                            task = create_async_task_safe(resource.close())
                            if task:
                                logger.info(f"Scheduled cleanup for {resource}")
                            else:
                                logger.info(
                                    f"Could not schedule cleanup for {resource}, trying direct run"
                                )
                                try:
                                    run_async_safely(resource.close())
                                except Exception as run_error:
                                    logger.error(
                                        f"Direct run failed for {resource}: {run_error}"
                                    )
                        else:
                            # No running loop, try asyncio.run in thread
                            logger.info(
                                f"Running cleanup for {resource} in thread as no event loop running"
                            )
                            try:
                                run_async_safely(resource.close())
                            except Exception as thread_error:
                                logger.error(
                                    f"Thread cleanup failed for {resource}: {thread_error}"
                                )
                    except RuntimeError as loop_error:
                        logger.error(
                            f"Could not access event loop for {resource}: {loop_error}"
                        )
                        # Mark resource as closed to prevent further issues
                        if hasattr(resource, "_closed"):
                            resource._closed = True
                else:
                    resource.close()
        except Exception as e:
            logger.warning(
                f"Warning: Could not clean up async resource {resource}: {e}"
            )
