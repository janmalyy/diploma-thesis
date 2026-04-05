import asyncio
import json
import os
import time
from typing import Optional

import dateutil.utils
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.responses import RedirectResponse

from diploma_thesis.api.clinvar import get_clinvar_urls
from diploma_thesis.api.variomes import (fetch_variomes_data,
                                         parse_variomes_data)
from diploma_thesis.core.models import (Variant, prune_articles,
                                        remove_articles_with_no_match)
from diploma_thesis.core.run_llm import run_pipeline
from diploma_thesis.core.update_article_fulltext import \
    update_articles_fulltext
from diploma_thesis.core.update_suppl_data import update_suppl_data
from diploma_thesis.settings import DATA_DIR, PACKAGE_DIR, logger
from diploma_thesis.utils.helpers import end, get_omim_url
from diploma_thesis.utils.upload_to_drive import upload_json_to_drive

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

    async def fetch_external_links(variant: Variant) -> dict:
        clinvar_urls = await asyncio.to_thread(get_clinvar_urls, variant.variant_string)
        omim_url = get_omim_url(variant.gene)
        return {"clinvar_urls": clinvar_urls, "omim_url": omim_url, "gene": variant.gene}

    async def event_generator():
        pipeline_task = None
        synvar_error_msg = None

        variant_info = {}
        start = time.time()

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
                synvar_error_msg = str(e)
                logger.info(f"SynVar error: {e}")
                logger.info("We try to continue with the pipeline, but the results might be less accurate.")

            # 2. Article Retrieval
            if await request.is_disconnected():
                return

            yield f"data: {json.dumps({'status': 'Fetching literature mentions'})}\n\n"
            try:
                data = fetch_variomes_data(variant)
                articles = parse_variomes_data(data, variant)
            except Exception as e:
                logger.error(f"Variomes API error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                return

            if not articles:
                if synvar_error_msg:
                    yield f"data: {json.dumps({'error': synvar_error_msg})}\n\n"
                    return

                yield f"data: {json.dumps({'status': 'Fetching External Links (ClinVar, OMIM)'})}\n\n"
                external_links = await fetch_external_links(variant)
                result = {"narrative_summary": "No articles found.", **external_links}
                yield f"data: {json.dumps({'result': result})}\n\n"
                return

            variant_info.update({"articles_before_pruning": len(articles)})
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

            n_articles = len(articles)
            variant_info.update({"articles_before_removing": n_articles})
            articles = remove_articles_with_no_match(articles)
            variant_info.update({
                "variant": variant.variant_string,
                "time_to_process_articles": end(start),
                "context_length": len("\n".join(str(article.get_structured_context()) for article in articles)),
                "articles_after_removal": len(articles),
                "only_medline_count": len([a for a in articles if a.data_sources == {"medline"}]),
                "only_pmc_count": len([a for a in articles if a.data_sources == {"pmc"}]),
                "only_suppl_count": len([a for a in articles if a.data_sources == {"suppl"}]),
                "both_pmc_and_supplcount": len([a for a in articles if a.data_sources == {"suppl", "pmc"}]),
                "all_three_count": len([a for a in articles if a.data_sources == {"suppl", "pmc", "medline"}]),
                "articles":
                    [
                        {
                            "pmid": a.pmid,
                            "pmcid": a.pmcid,
                            "data_sources": [source for source in a.data_sources],
                            "source_of_annotation": a.annotation_source,
                            "title_length": len(a.title),
                            "abstract_length": len(a.abstract),
                            "number_of_unmatched_snippets": len(a.fulltext_snippets),
                            "unmatched_snippets": [s.machine_comparable for s in a.fulltext_snippets],
                            "number_of_paragraphs": len(a.paragraphs),
                            "paragraphs_lengths": [len(p) for p in a.paragraphs],

                            "number_of_suppl_files": len(a.suppl_data_list),
                            "suppl_paragraphs_counts_per_file": [len(sd.paragraphs) for sd in a.suppl_data_list],
                            "suppl_paragraphs_lengths": [[len(str(p)) for p in sd.paragraphs] for sd in
                                                         a.suppl_data_list],
                        }
                        for a in articles
                    ],
            })

            if n_articles == 0:
                yield f"data: {json.dumps({'status': 'Fetching External Links (ClinVar, OMIM)'})}\n\n"
                external_links = await fetch_external_links(variant)
                result = {"narrative_summary": "No articles matched filtering.", **external_links}
                yield f"data: {json.dumps({'result': result})}\n\n"
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

            # 5. Add External Links
            yield f"data: {json.dumps({'status': 'Fetching External Links (ClinVar, OMIM)'})}\n\n"
            external_links = await fetch_external_links(variant)
            final_result.update(external_links)

            yield f"data: {json.dumps({'result': final_result})}\n\n"

            variant_info.update(
                final_result,
            )
            variant_info.update(
                {"total_time": end(start)}
            )

            filename = f"{variant.variant_string}_{dateutil.utils.today().date()}_{time.time()}_variant_info.json"

            try:
                upload_json_to_drive(variant_info, filename)
            except Exception as e:
                logger.error(f"Error uploading variant_info to Google Drive: {e}")

            # try:
            #     (DATA_DIR / "results").mkdir(parents=True, exist_ok=True)
            #     with open(DATA_DIR / "results" / filename, "w", encoding="utf-8") as f:
            #         json.dump(variant_info, f, indent=4)
            # except Exception as e:
            #     logger.error(f"Error uploading variant_info to local storage : {e}")

        except asyncio.CancelledError:
            logger.info("Pipeline execution cancelled due to client disconnect.")
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'error': 'We are sorry:( Pipeline error:' + str(e)})}\n\n"
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
