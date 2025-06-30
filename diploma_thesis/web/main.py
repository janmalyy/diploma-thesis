from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from diploma_thesis.settings import PACKAGE_DIR

app = FastAPI()

# we don't need the static dir yet
# app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "diploma_thesis" / "web" / "static"), name="static")

templates = Jinja2Templates(directory=PACKAGE_DIR / "diploma_thesis" / "web" / "templates")


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    """
    Serves the index.html file at the root URL.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/display-graph/")
async def display_graph():
    pass
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
