import asyncio
import json
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
def root():
    return RedirectResponse(url="/variant", status_code=302)


@app.get("/variant", response_class=HTMLResponse)
def get_variant_summary(request: Request):
    return templates.TemplateResponse(request=request, name="variant_summary.html")


class VariantRequest(BaseModel):
    gene: Optional[str] = None
    change: str
    level: str


@app.post("/api/generate-llm-summary")
async def generate_llm_summary(request: VariantRequest):
    async def event_generator():
        try:
            # 1. Initialization and SynVar Fetch
            yield f"data: {json.dumps({'status': 'Recognizing the variant (SynVar)'})}\n\n"
            try:
                variant = Variant(request.gene, request.change, request.level, fetch_data=False)
                variant.fetch_synvar_data(request.level)
            except Exception as e:
                logger.error(f"SynVar error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                return

            # 2. Article Retrieval
            yield f"data: {json.dumps({'status': 'Fetching literature mentions'})}\n\n"
            data = fetch_variomes_data(variant)
            articles = parse_variomes_data(data, variant)
            if not articles:
                yield f"data: {json.dumps({'result': 'No articles found.'})}\n\n"
                return

            articles = prune_articles(articles)

            # 3. Content Update
            yield f"data: {json.dumps({'status': 'Updating Fulltext & Suppl Data'})}\n\n"
            await asyncio.gather(
                asyncio.to_thread(update_articles_fulltext, articles, variant),
                asyncio.to_thread(update_suppl_data, articles, variant)
            )

            articles = remove_articles_with_no_match(articles)
            n_articles = len(articles)
            if n_articles == 0:
                yield f"data: {json.dumps({'result': 'No articles matched filtering.'})}\n\n"
                return

            # 4. LLM Pipeline with Monotonic Counter
            total_llm_calls = n_articles + 1
            yield f"data: {json.dumps({
                'status': 'Analysis and Extraction',
                'article_count': n_articles,
                'total_calls': total_llm_calls,
                'completed_calls': 0
            })}\n\n"

            queue = asyncio.Queue()
            completed_count = 0

            async def progress_callback_queue(phase):
                await queue.put(phase)

            pipeline_task = asyncio.create_task(run_pipeline(variant, articles, progress_callback_queue))

            while not pipeline_task.done() or not queue.empty():
                try:
                    phase = await asyncio.wait_for(queue.get(), timeout=0.2)
                    completed_count += 1

                    yield f"data: {json.dumps({
                        'status': f'{phase}: {completed_count}/{total_llm_calls}',
                        'completed_calls': completed_count,
                        'total_calls': total_llm_calls,
                        'phase': phase
                    })}\n\n"
                except asyncio.TimeoutError:
                    continue

            final_result = await pipeline_task
            yield f"data: {json.dumps({'result': final_result})}\n\n"

        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run("diploma_thesis.web.main:app", host="0.0.0.0", port=8000, reload=True)
