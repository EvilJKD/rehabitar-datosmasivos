"""Compatibilidad ligera de Pydantic para ejecutar pruebas unitarias sin dependencias web."""

from datetime import date, datetime
from typing import Any, Callable, Dict, Optional

try:
    from pydantic import BaseModel, ConfigDict, Field
    PYDANTIC_AVAILABLE = True
except ImportError:  # pragma: no cover - permite ejecutar pruebas unitarias en host sin pydantic
    PYDANTIC_AVAILABLE = False

    def ConfigDict(**kwargs: Any) -> Dict[str, Any]:  # type: ignore
        return kwargs

    class _DefaultFactory:
        def __init__(self, factory: Callable[[], Any]):
            self.factory = factory

    def _serialize_json(value: Any) -> Any:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, list):
            return [_serialize_json(item) for item in value]
        if isinstance(value, dict):
            return {k: _serialize_json(v) for k, v in value.items()}
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        return value

    class BaseModel:  # type: ignore
        def __init__(self, **data: Any):
            for cls in reversed(type(self).__mro__):
                if cls is object or cls is BaseModel:
                    continue
                for attr_name, attr_val in cls.__dict__.items():
                    if attr_name.startswith("_") or attr_name == "model_config":
                        continue
                    if isinstance(attr_val, _DefaultFactory):
                        setattr(self, attr_name, attr_val.factory())
                    elif not callable(attr_val) and not isinstance(
                        attr_val, (staticmethod, classmethod, property)
                    ):
                        setattr(self, attr_name, attr_val)
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
            raw = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
            if kwargs.get("mode") == "json":
                return {k: _serialize_json(v) for k, v in raw.items()}
            return raw

        def dict(self, **kwargs: Any) -> Dict[str, Any]:
            return self.model_dump(**kwargs)

    def Field(  # type: ignore
        default: Any = None,
        *,
        default_factory: Optional[Callable[[], Any]] = None,
        **kwargs: Any,
    ) -> Any:
        if default_factory is not None:
            return _DefaultFactory(default_factory)
        return None if default is Ellipsis else default
