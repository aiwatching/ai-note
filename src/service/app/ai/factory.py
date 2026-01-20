"""AI service factory."""
from typing import Dict, Type

from .base import AIServiceBase
from .claude_service import ClaudeService
from .deepseek_service import DeepSeekService


class AIServiceFactory:
    """Factory for creating AI service instances."""

    _services: Dict[str, Type[AIServiceBase]] = {
        "claude": ClaudeService,
        "deepseek": DeepSeekService,
    }

    @classmethod
    def create(cls, service_type: str, **kwargs) -> AIServiceBase:
        """
        Create an AI service instance.

        Args:
            service_type: Type of service ('claude', 'openai', etc.)
            **kwargs: Service configuration (api_key, model, etc.)

        Returns:
            AI service instance

        Raises:
            ValueError: If service type is not supported
        """
        service_class = cls._services.get(service_type)
        if not service_class:
            raise ValueError(f"Unsupported AI service type: {service_type}")

        return service_class(**kwargs)

    @classmethod
    def register(cls, name: str, service_class: Type[AIServiceBase]):
        """
        Register a new AI service type.

        Args:
            name: Service type name
            service_class: Service class
        """
        cls._services[name] = service_class

    @classmethod
    def available_services(cls) -> list:
        """Get list of available service types."""
        return list(cls._services.keys())
