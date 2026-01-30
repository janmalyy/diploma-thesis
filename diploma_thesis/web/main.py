import os
import io
import tempfile
from typing import List, Optional, Any

import pandas as pd
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from pydantic import BaseModel
from starlette.responses import RedirectResponse

from diploma_thesis.api.einfra import run_einfra, build_prompt
from diploma_thesis.settings import PACKAGE_DIR, logger
from diploma_thesis.api.convert_ids import convert_ids, connect_pubmed_ids_with_links

app = FastAPI()
app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "web" / "static"), name="static")
templates = Jinja2Templates(directory=PACKAGE_DIR / "web" / "templates")


@app.get("/")
def root():
    return RedirectResponse(url="/excel", status_code=302)


@app.get("/excel", response_class=HTMLResponse)
def get_excel_viewer(request: Request):
    return templates.TemplateResponse(request=request, name="excel_viewer.html")


class ExcelExportRequest(BaseModel):
    data: List[List[Optional[Any]]]
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
    ids: List[str]


@app.post("/api/pubmed/convert")
async def convert_pubmed_ids(request: PubmedIdsRequest):
    try:
        converted_ids = convert_ids(request.ids, "pmid")

        result = connect_pubmed_ids_with_links(converted_ids)

        return {"result": dict(result)}
    except Exception as e:
        logger.error(f"Error converting PubMed IDs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error converting PubMed IDs: {str(e)}")


class RowIdRequest(BaseModel):
    row_id: str


@app.post("/api/excel/generate-llm-summary")
async def generate_llm_summary(request: RowIdRequest):
    """WIP: just mocks the function logic for now."""
    try:
        # row_id = request.row_id
        # return {"result": f"Generated llm summary for this row_id: {row_id}."}
        # TODO get the true ids_list, this is just a hardcoded example
        ids_list = [26801900, 24944790, 19104657, 26099996]
        gene_symbol = "BRCA1"
        variant = "3_149238596_-/TTAA"
        converted_ids_dict = convert_ids(ids_list, "pmid")
        context = """this is mocked context. Please return: 'WIP, add context'."""
        prompt = build_prompt(context, gene_symbol, variant)
        response = await run_einfra(prompt, model_name="gpt-oss-120b")
        return {"result": response}

    except Exception as e:
        logger.error(f"Error generating LLM summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating LLM summary: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("diploma_thesis.web.main:app", host="0.0.0.0", port=8000, reload=True)
