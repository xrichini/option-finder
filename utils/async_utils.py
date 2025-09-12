# utils/async_utils.py
import asyncio
import concurrent.futures
import functools
import streamlit as st
import nest_asyncio
from typing import Any, Coroutine, Callable, TypeVar, Optional
import warnings

# Apply nest_asyncio at module level
nest_asyncio.apply()

T = TypeVar('T')

def run_async_in_streamlit(coro: Coroutine[Any, Any, T], timeout: Optional[float] = 30) -> T:
    """
    Safely run an async coroutine in a Streamlit environment.
    
    This function handles the complexity of running async code in Streamlit
    which already runs in an event loop (Tornado).
    
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
            # If we're in a running loop (like in Streamlit), we need to be careful
            # We'll run the coroutine in a thread pool to avoid blocking
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=timeout)
        else:
            # If no loop is running, we can safely use asyncio.run
            return asyncio.run(coro)
            
    except RuntimeError as e:
        error_msg = str(e).lower()
        if "already running" in error_msg or "cannot be called from a running event loop" in error_msg:
            # Fallback: run in thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=timeout)
        else:
            raise
    except Exception as e:
        # Log the error for debugging
        st.error(f"Error running async operation: {str(e)}")
        raise

def create_async_task_safe(coro: Coroutine, name: Optional[str] = None) -> Optional[asyncio.Task]:
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
    Decorator to convert an async function to sync for use in Streamlit.
    
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
        return run_async_in_streamlit(coro)
    
    return wrapper

class AsyncContextManager:
    """
    Context manager to handle async resources safely in Streamlit.
    
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
                if hasattr(resource, 'close'):
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()
            except Exception as e:
                print(f"Warning: Error cleaning up resource {resource}: {e}")
        self.resources.clear()

def safe_async_run_with_fallback(async_func: Callable, sync_fallback: Callable, *args, **kwargs):
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
            return run_async_in_streamlit(coro)
        else:
            return async_func(*args, **kwargs)
    except (RuntimeError, asyncio.TimeoutError) as e:
        if "event loop" in str(e).lower() or "timeout" in str(e).lower():
            # Fall back to sync version
            return sync_fallback(*args, **kwargs)
        else:
            raise

def cleanup_session_async_resources():
    """Clean up any async resources stored in Streamlit session state"""
    cleanup_keys = []
    
    for key, value in st.session_state.items():
        if hasattr(value, '_session') and hasattr(value, 'close'):
            # This looks like an async client
            cleanup_keys.append(key)
            
    for key in cleanup_keys:
        try:
            client = st.session_state[key]
            # Try to close the client
            if hasattr(client, 'close'):
                if asyncio.iscoroutinefunction(client.close):
                    # Try to handle async cleanup safely
                    try:
                        # First try to get the event loop
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Try to create a task
                            task = create_async_task_safe(client.close())
                            if task:
                                print(f"Scheduled cleanup for {key}")
                            else:
                                print(f"Could not schedule cleanup for {key}, trying direct run")
                                try:
                                    run_async_in_streamlit(client.close())
                                except Exception as run_error:
                                    print(f"Direct run failed for {key}: {run_error}")
                        else:
                            # No running loop, try asyncio.run in thread
                            print(f"Running cleanup for {key} in thread as no event loop running")
                            try:
                                run_async_in_streamlit(client.close())
                            except Exception as thread_error:
                                print(f"Thread cleanup failed for {key}: {thread_error}")
                    except RuntimeError as loop_error:
                        print(f"Could not access event loop for {key}: {loop_error}")
                        # Mark client as closed to prevent further issues
                        if hasattr(client, '_closed'):
                            client._closed = True
                else:
                    client.close()
            del st.session_state[key]
        except Exception as e:
            print(f"Warning: Could not clean up async resource {key}: {e}")
            # Still try to remove from session state
            try:
                del st.session_state[key]
            except:
                pass
