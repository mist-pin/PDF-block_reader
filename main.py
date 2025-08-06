from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from utils import BasePDFProcessor, ShadowfaxPDFProcessor
import httpx
from io import BytesIO
import uvicorn
import asyncio
import traceback






app = FastAPI()
# ===============================================
# =============== Helper Functions ==============
# ===============================================
async def get_pdf_from_url(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return BytesIO(response.content)






# ===============================================
# =============== Data Models ===================
# ===============================================
class Extract_RequestModel(BaseModel):
    company_id: str
    urls: str | list[str]

class Extract_ResponseModel(BaseModel):
    class ResponseDict(BaseModel):
        url: HttpUrl | list[HttpUrl]
        message: str
        data: dict | list | str | None

    company_id: str
    data: list[ResponseDict]





# ===============================================
# =============== Endpoints ====================
# ===============================================
@app.post("/api/v1/pdf/label/extract", response_model=Extract_ResponseModel)
async def extract_label(payload: Extract_RequestModel):
    result = Extract_ResponseModel(company_id=payload.company_id, data=[])

    payload.urls = [payload.urls] if isinstance(payload.urls, str) else payload.urls

    pdf_bytes_list = await asyncio.gather(*[get_pdf_from_url(url) for url in payload.urls])
    for url, pdf_bytes in zip(payload.urls, pdf_bytes_list):
        try:
            if not isinstance(pdf_bytes, BytesIO):
                raise ValueError("pdf download failed", pdf_bytes)
            
            # First check if it's a ShadowFax label
            pdf_processor = BasePDFProcessor(pdf_bytes)
            if pdf_processor.get_label_shipper() == "shadowfax":
                # Pass the PDF bytes directly to ShadowfaxPDFProcessor
                extracted_data = ShadowfaxPDFProcessor(pdf_bytes).result
                result.data.append(Extract_ResponseModel.ResponseDict(url=url, message="success", data=extracted_data))
            else:
                result.data.append(Extract_ResponseModel.ResponseDict(url=url, message="unknown shipper", data=None))
        except Exception as e:
            traceback.print_exc()
            result.data.append(Extract_ResponseModel.ResponseDict(url=url, message=str(e), data=None))
    return result



if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=4000, reload=True)





# ===============================================
# =============== File Download Endpoint ========
# ===============================================
@app.get("/api/v1/get_pdf")
async def download_file():
    """
    Download a file by name from the server
    """
    file_path = f"/home/alchemist/Downloads/meesho_label.pdf"

    return FileResponse(
        path=file_path,
        filename="meesho_label.pdf",
        media_type='application/octet-stream'
    )
