import neo4j
from fastapi import HTTPException

from diploma_thesis.settings import logger


class CypherSyntaxError(HTTPException):
    """Raised when the user submits a query with invalid syntax."""
    def __init__(self, message: str):
        self.detail = f"Invalid syntax for submitted Cypher query: {message}"
        logger.error(f"CypherSyntaxError logged: {message}")
        super().__init__(status_code=400, detail=self.detail)

