from fastapi import Request
from fastapi.responses import JSONResponse

from diploma_thesis.web.exceptions import CypherSyntaxError


def register_error_handlers(app):
    @app.exception_handler(CypherSyntaxError)
    async def handle_cypher_syntax_error(request: Request, exception: CypherSyntaxError):
        return JSONResponse(
            status_code=400,
            content={"detail": exception.detail
                     },
        )
