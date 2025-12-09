from typing import Callable, Dict, Any, Optional
import functools

class ToolRegistry:
    _registry: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: Optional[str] = None):
        def decorator(func: Callable):
            tool_name = name or func.__name__
            cls._registry[tool_name] = func
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    @classmethod
    def get_tool(cls, name: str) -> Optional[Callable]:
        return cls._registry.get(name)

    @classmethod
    def list_tools(cls) -> Dict[str, str]:
        return {name: func.__doc__ or "No description" for name, func in cls._registry.items()}
    
    @classmethod
    def exists(cls, name: str) -> bool:
        return name in cls._registry

# Global instance not strictly needed as methods are classmethods, but good for consistency if we want to instantiate later.
registry = ToolRegistry()
