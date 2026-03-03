import asyncio
import io
import json
import os
import tempfile
from typing import Any, Optional

import pandas as pd
import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.responses import RedirectResponse

from diploma_thesis.api.convert_ids import (connect_pubmed_ids_with_links,
                                            convert_ids)
from diploma_thesis.api.einfra import run_einfra
from diploma_thesis.api.variomes import (fetch_variomes_data,
                                         parse_variomes_data)
from diploma_thesis.core.models import Variant
from diploma_thesis.core.run_llm import (aggregate_evidences,
                                         extract_evidences, relevance_check)
from diploma_thesis.core.update_article_fulltext import \
    update_articles_fulltext
from diploma_thesis.core.update_suppl_data import update_suppl_data
from diploma_thesis.settings import PACKAGE_DIR, logger

app = FastAPI()
app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "web" / "static"), name="static")
templates = Jinja2Templates(directory=PACKAGE_DIR / "web" / "templates")


@app.get("/")
def root():
    return RedirectResponse(url="/excel", status_code=302)


@app.get("/excel", response_class=HTMLResponse)
def get_excel_viewer(request: Request):
    return templates.TemplateResponse(request=request, name="excel_viewer.html")


@app.get("/variant", response_class=HTMLResponse)
def get_variant_summary(request: Request):
    return templates.TemplateResponse(request=request, name="variant_summary.html")


class ExcelExportRequest(BaseModel):
    data: list[list[Optional[Any]]]
    filename: str


@app.post("/api/excel/upload")
async def upload_excel_file(file: UploadFile = File(...)):
    # Check file extension
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    try:
        # Save uploaded file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # Read Excel file with pandas
        df = pd.read_excel(temp_file_path)

        # Convert DataFrame to list of lists for JSON serialization
        data = df.fillna('').values.tolist()

        # Add column headers as first row if they exist
        if not df.columns.empty and not all(col.startswith('Unnamed:') for col in df.columns):
            headers = df.columns.tolist()
            data.insert(0, headers)

        # Clean up temporary file
        os.unlink(temp_file_path)

        return {"filename": file.filename, "data": data}

    except Exception as e:
        # Clean up temporary file if it exists
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)

        logger.error(f"Error processing Excel file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing Excel file: {str(e)}")


@app.post("/api/excel/export/xlsx")
async def export_excel_xlsx(request: ExcelExportRequest):
    try:
        # Check for empty data
        if not request.data:
            raise HTTPException(status_code=400, detail="Input data cannot be empty.")

        # Extract headers (first row) and actual data rows (rest)
        headers = request.data[0]
        data_rows = request.data[1:]

        # Convert data to DataFrame
        df = pd.DataFrame(data_rows, columns=headers)

        # Ensure DataFrame is not empty (e.g., only headers were sent)
        if df.empty:
            # Create an empty DataFrame with the correct column names
            df = pd.DataFrame(columns=headers)

        # Create a BytesIO object to store the Excel file
        output = io.BytesIO()

        # Write DataFrame to Excel
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # We explicitly check for empty data here to avoid the "At least one sheet must be visible" error
            # when writing an empty df with headers.
            df.to_excel(writer, index=False,
                        sheet_name='Sheet1')  # Removed encoding='utf-8', as it's not needed/supported here

        # Set up the response
        output.seek(0)

        # Return the Excel file as a streaming response
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={request.filename}"}
        )

    except Exception as e:
        logger.error(f"Error exporting Excel file: {str(e)}")
        # If the original error was about empty sheet, give a better error message to the user
        if "At least one sheet must be visible" in str(e):
            raise HTTPException(status_code=500,
                                detail="Error exporting: Data is likely empty or improperly formatted.")
        raise HTTPException(status_code=500, detail=f"Error exporting Excel file: {str(e)}")


@app.post("/api/excel/export/csv")
async def export_excel_csv(request: ExcelExportRequest):
    try:
        if not request.data:
            raise HTTPException(status_code=400, detail="Input data cannot be empty.")

        # Extract headers (first row) and actual data rows (rest)
        headers = request.data[0]
        data_rows = request.data[1:]

        # Convert data to DataFrame
        df = pd.DataFrame(data_rows, columns=headers)

        # Create a StringIO object to store the CSV file
        output = io.StringIO()

        # Write DataFrame to CSV (Note: Pandas defaults to utf-8, which is good)
        df.to_csv(output, index=False, encoding="utf-8")

        # Set up the response: IMPORTANT: Explicitly encode output using UTF-8
        output_bytes = io.BytesIO(output.getvalue().encode('utf-8'))

        # Return the CSV file as a streaming response
        return StreamingResponse(
            output_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={request.filename}"}
        )

    except Exception as e:
        logger.error(f"Error exporting CSV file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error exporting CSV file: {str(e)}")


class PubmedIdsRequest(BaseModel):
    ids: list[str]


@app.post("/api/pubmed/convert")
async def convert_pubmed_ids(request: PubmedIdsRequest):
    try:
        converted_ids = convert_ids(request.ids, "pmid")

        result = connect_pubmed_ids_with_links(converted_ids)

        return {"result": dict(result)}
    except Exception as e:
        logger.error(f"Error converting PubMed IDs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error converting PubMed IDs: {str(e)}")


class VariantRequest(BaseModel):
    gene: Optional[str] = None
    change: str
    level: str


@app.post("/api/generate-llm-summary")
async def generate_llm_summary(request: VariantRequest):
    async def event_generator():
        try:
            yield f"data: {json.dumps({'status': 'SynVar fetch'})}\n\n"
            variant = Variant(request.gene, request.change, request.level, fetch_data=False)
            variant.fetch_synvar_data(request.level)
            logger.info(f"Processing variant: {variant}")

            yield f"data: {json.dumps({'status': 'SIBiLS fetch'})}\n\n"
            data = fetch_variomes_data(variant)
            articles = parse_variomes_data(data, variant)

            if not articles:
                yield f"data: {json.dumps({'result': 'No articles found for this variant in SIBiLS Variomes.'})}\n\n"
                return

            yield f"data: {json.dumps({'status': 'Annotation', 'article_count': len(articles)})}\n\n"
            logger.info(f"Found {len(articles)} articles. IDs: {[a.pmcid if a.pmcid != '' else a.pmid for a in articles]}")

            # Total LLM calls estimate:
            # - relevance_check: len(articles)
            # - extract_evidences: roughly len(articles)/2 (guess) + 1 for aggregation
            # We will update total_calls as we know more.
            total_llm_calls = len(articles) + 1 # Initial estimate
            yield f"data: {json.dumps({'total_calls': total_llm_calls})}\n\n"

            logger.info("Fetching data from PubTator and BiodiversityPMC...")
            try:
                update_articles_fulltext(articles)
            except Exception as e:
                logger.error(f"Error updating fulltext: {e}")

            try:
                update_suppl_data(articles, variant)
            except Exception as e:
                logger.error(f"Error updating supplementary data: {e}")

            queue = asyncio.Queue()

            async def progress_callback_queue(current, phase):
                await queue.put({"current": current, "phase": phase})

            # Start relevance check in a task
            task = asyncio.create_task(relevance_check(variant, articles, progress_callback_queue))

            completed_calls = 0
            while not task.done():
                try:
                    # Wait for a progress message with timeout to keep the loop alive
                    msg = await asyncio.wait_for(queue.get(), timeout=0.1)
                    completed_calls = msg["current"]
                    yield f"data: {json.dumps({'status': f'{msg['phase']}: {msg['current']}/{len(articles)}', 'completed_calls': completed_calls})}\n\n"
                except asyncio.TimeoutError:
                    continue

            # Process any remaining messages in the queue
            while not queue.empty():
                msg = await queue.get()
                completed_calls = msg["current"]
                yield f"data: {json.dumps({'status': f'{msg['phase']}: {msg['current']}/{len(articles)}', 'completed_calls': completed_calls})}\n\n"

            relevant_articles = await task

            if not relevant_articles:
                yield f"data: {json.dumps({'result': f'None of the {len(articles)} articles found were identified as relevant by the LLM.'})}\n\n"
                return

            # Now we know how many relevant articles there are, update total_calls
            relevance_calls = len(articles)
            extraction_calls = len(relevant_articles)
            aggregation_calls = 1
            total_llm_calls = relevance_calls + extraction_calls + aggregation_calls
            yield f"data: {json.dumps({'total_calls': total_llm_calls, 'completed_calls': relevance_calls})}\n\n"

            # Evidence extraction
            task = asyncio.create_task(extract_evidences(variant, relevant_articles, progress_callback_queue))
            yield f"data: {json.dumps({'article_count': len(relevant_articles), 'phase': 'relevant articles'})}\n\n"

            while not task.done():
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=0.1)
                    completed_calls = relevance_calls + msg["current"]
                    yield f"data: {json.dumps({'status': f'{msg['phase']}: {msg['current']}/{len(relevant_articles)}', 'completed_calls': completed_calls})}\n\n"
                except asyncio.TimeoutError:
                    continue

            while not queue.empty():
                msg = await queue.get()
                completed_calls = relevance_calls + msg["current"]
                yield f"data: {json.dumps({'status': f'{msg['phase']}: {msg['current']}/{len(relevant_articles)}', 'completed_calls': completed_calls})}\n\n"

            evidences = await task
            if not evidences:
                yield f"data: {json.dumps({'result': f'Failed to extract any structured evidence from the {len(relevant_articles)} relevant articles.'})}\n\n"
                return

            yield f"data: {json.dumps({'status': 'Aggregation', 'completed_calls': relevance_calls + extraction_calls, 'article_count': 0})}\n\n"
            aggregated_evidence = await aggregate_evidences(variant, evidences)
            yield f"data: {json.dumps({'completed_calls': total_llm_calls})}\n\n"

            # Return the full aggregated evidence dictionary
            if isinstance(aggregated_evidence, dict):
                aggregated_evidence["article_evidences"] = evidences
                yield f"data: {json.dumps({'result': aggregated_evidence})}\n\n"
            else:
                yield f"data: {json.dumps({'result': {'narrative_summary': str(aggregated_evidence), 'structured_summary': None, 'article_evidences': evidences}})}\n\n"

        except Exception as e:
            logger.error(f"Error generating LLM summary: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run("diploma_thesis.web.main:app", host="0.0.0.0", port=8000, reload=True)
