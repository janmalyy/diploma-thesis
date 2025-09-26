from fastapi import HTTPException

from diploma_thesis.settings import logger


class CypherSyntaxError(HTTPException):
    """Raised when the user submits a query with invalid syntax."""
    def __init__(self, message: str):
        self.detail = f"Invalid syntax for submitted Cypher query: {message}"
        logger.error(f"CypherSyntaxError logged: {message}")
        super().__init__(status_code=400, detail=self.detail)


class NeoNotAvailableError(HTTPException):
    """Raised when the database is unavailable."""
    def __init__(self):
        self.detail = f"The database is not available. Please ensure the connection is started and properly working and try again."
        logger.error(f"NeoNotReadyError logged: {self.detail}")
        super().__init__(status_code=400, detail=self.detail)
