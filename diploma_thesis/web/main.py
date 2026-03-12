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
