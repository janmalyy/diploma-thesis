from fastapi import Request
from fastapi.responses import JSONResponse

from diploma_thesis.web.exceptions import CypherSyntaxError, NeoNotAvailableError


def register_error_handlers(app):
    @app.exception_handler(CypherSyntaxError)
    async def handle_cypher_syntax_error(request: Request, exception: CypherSyntaxError):
        return JSONResponse(
            status_code=400,
            content={"detail": exception.detail
                     },
        )

    @app.exception_handler(NeoNotAvailableError)
    async def handle_neo_not_available_error(request: Request, exception: NeoNotAvailableError):
        return JSONResponse(
            status_code=400,
            content={"detail": exception.detail
                     },
        )

