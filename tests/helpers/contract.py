from typing import Type, Any
from pydantic import BaseModel

def validate_response_schema(data: Any, schema: Type[BaseModel]):
    if isinstance(data, dict):
        schema.model_validate(data)
    elif isinstance(data, list):
        for item in data:
            schema.model_validate(item)
    else:
        schema.model_validate(data)