import asyncio
import json
import os
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.responses import RedirectResponse

from diploma_thesis.api.variomes import (fetch_variomes_data,
                                         parse_variomes_data)
from diploma_thesis.core.models import (Variant, prune_articles,
                                        remove_articles_with_no_match)
from diploma_thesis.core.run_llm import run_pipeline
from diploma_thesis.core.update_article_fulltext import \
    update_articles_fulltext
from diploma_thesis.core.update_suppl_data import update_suppl_data
from diploma_thesis.settings import PACKAGE_DIR, logger

app = FastAPI()
app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "web" / "static"), name="static")
templates = Jinja2Templates(directory=PACKAGE_DIR / "web" / "templates")


@app.get("/")
def root(request: Request):
    url = request.url_for("get_variant_summary")
    return RedirectResponse(url=url, status_code=302)


@app.get("/debug-paths")
async def debug_paths(request: Request):
    return {
        "base_url": str(request.base_url),
        "url_path": request.url.path,
        "root_path": request.scope.get("root_path"),
        "path_info": os.environ.get("PATH_INFO"),
        "script_name": os.environ.get("SCRIPT_NAME")
    }


@app.get("/variant", response_class=HTMLResponse)
def get_variant_summary(request: Request):
    return templates.TemplateResponse(request=request, name="variant_summary.html")


class VariantRequest(BaseModel):
    gene: Optional[str] = None
    change: str
    level: str


@app.post("/api/generate-llm-summary")
async def generate_llm_summary(request: Request, variant_request: VariantRequest):
    """
    Handles the streaming of LLM-generated variant summaries with constant connection monitoring.

    Args:
        request: The FastAPI Request object to monitor client connection.
        variant_request: The Pydantic model containing variant details.

    Returns:
        StreamingResponse: A server-sent events stream of status updates and results.
    """

    async def event_generator():
        pipeline_task = None
        try:
            # 1. Initialization and SynVar Fetch
            yield f"data: {json.dumps({'status': 'Recognizing the variant (SynVar)'})}\n\n"

            if await request.is_disconnected():
                return

            variant = Variant(
                variant_request.gene,
                variant_request.change,
                variant_request.level,
                fetch_data=False
            )

            # we fetch synvar data to get the variant name and gene
            try:
                variant.fetch_synvar_data()
            except Exception as e:
                logger.error(f"SynVar error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                return

            # 2. Article Retrieval
            if await request.is_disconnected():
                return

            yield f"data: {json.dumps({'status': 'Fetching literature mentions'})}\n\n"
            data = fetch_variomes_data(variant)
            articles = parse_variomes_data(data, variant)

            # we fetch also synvar after variomes, because there is more in the synvar response
            try:
                variant.fetch_synvar_data()
            except Exception as e:
                logger.error(f"SynVar error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                return

            if not articles:
                yield f"data: {json.dumps({'result': 'No articles found.'})}\n\n"
                return

            articles = prune_articles(articles)

            # 3. Content Update
            if await request.is_disconnected():
                return

            yield f"data: {json.dumps({'status': 'Updating Fulltext & Suppl Data'})}\n\n"

            await asyncio.gather(
                asyncio.to_thread(update_articles_fulltext, articles, variant),
                asyncio.to_thread(update_suppl_data, articles, variant)
            )

            if await request.is_disconnected():
                logger.info("Client disconnected after article updates.")
                return

            articles = remove_articles_with_no_match(articles)
            n_articles = len(articles)
            if n_articles == 0:
                yield f"""data: {json.dumps({'result': 'No articles matched filtering.'})}\n\n"""
                return

            # 4. LLM Pipeline with constant monitoring
            total_llm_calls = n_articles + 1
            yield f"""data: {json.dumps({
                'status': 'Analysis and Extraction',
                'article_count': n_articles,
                'total_calls': total_llm_calls,
                'completed_calls': 0
            })}\n\n"""

            queue = asyncio.Queue()
            completed_count = 0

            async def progress_callback_queue(phase: str):
                await queue.put(phase)

            pipeline_task = asyncio.create_task(
                run_pipeline(variant, articles, progress_callback_queue)
            )

            while not pipeline_task.done() or not queue.empty():
                if await request.is_disconnected():
                    logger.info("Client disconnected during LLM pipeline.")
                    pipeline_task.cancel()
                    return

                try:
                    phase = await asyncio.wait_for(queue.get(), timeout=0.1)
                    completed_count += 1

                    yield f"""data: {json.dumps({
                        'status': f'{phase}: {completed_count}/{total_llm_calls}',
                        'completed_calls': completed_count,
                        'total_calls': total_llm_calls,
                        'phase': phase
                    })}\n\n"""
                except asyncio.TimeoutError:
                    continue

            final_result = await pipeline_task
            yield f"data: {json.dumps({'result': final_result})}\n\n"

        except asyncio.CancelledError:
            logger.info("Pipeline execution cancelled due to client disconnect.")
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            if pipeline_task and not pipeline_task.done():
                pipeline_task.cancel()
                try:
                    await pipeline_task
                except asyncio.CancelledError:
                    pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run("diploma_thesis.web.main:app", host="0.0.0.0", port=8000, reload=True)
