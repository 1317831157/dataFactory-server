import functools
import logging
from pydantic import PydanticUserError, PydanticSchemaGenerationError

logger = logging.getLogger(__name__)

def handle_pydantic_errors(func):
    """装饰器，用于捕获和记录 Pydantic 相关错误"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except PydanticUserError as e:
            logger.error(f"Pydantic user error: {e.code} - {e}")
            raise
        except PydanticSchemaGenerationError as e:
            logger.error(f"Pydantic schema generation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
    return wrapper