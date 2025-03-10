import os
import json
import re
from typing import Dict, Any

import httpx
import pdfplumber
from fastapi import APIRouter, UploadFile, File, HTTPException
import io
from app.utils.logger import logger

router = APIRouter()

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

async def generate_summary(text: str) -> Dict:
    """
    Generate a standardized summary using OpenRouter AI
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://your-site.com",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Please analyze this document and extract key information in a structured format.
    Return only a JSON object with an approptiate structure:. keep two nodes for summary and recommendations, apart from other data.
    Document text:
    {text}
    """

    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Generating summary with OpenRouter API")
            response = await client.post(
                OPENROUTER_URL,
                headers=headers,
                json={
                    "model": "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
                    "messages": [
                        {"role": "system", "content": "You are a medical report analyzer that returns structured JSON only."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            
            if response.status_code != 200:
                logger.error(f"OpenRouter API error: {response.text}")
                raise HTTPException(status_code=500, detail="Error generating summary")
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            try:
                pattern = r"<think>([^<]*)<\/think>.*```json([^`]*)```"
                match = re.search(pattern, content, re.DOTALL)
                
                if match:
                    json_str = match.group(2)
                    meta_str = match.group(1)
                    json_obj = json.loads(json_str)
                    json_obj['think'] = meta_str
                else:
                    json_obj = {'content': content}
                
                logger.info(f"Generated summary: {json.dumps(json_obj, indent=4)}")
                return json_obj
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {str(e)}")
                raise HTTPException(status_code=500, detail="Invalid response format")
                
    except Exception as e:
        logger.error(f"Error calling OpenRouter API: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating summary")

@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload a PDF file and extract its text content.
    
    Args:
        file: The PDF file to be processed
        
    Returns:
        Dict containing the extracted text, metadata, and AI-generated summary
    """
    if not file.filename.endswith('.pdf'):
        logger.warning(f"Invalid file type attempted: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        logger.info(f"Processing file: {file.filename}")
        contents = await file.read()
        
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            metadata = pdf.metadata or {}
            extracted_text = ""
            
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                extracted_text += page_text + "\n\n"

            logger.info(f"Extracted text from file")

            extracted_json = await generate_summary(extracted_text)
            
            response = {
                "filename": file.filename,
                "text": extracted_text,
                "metadata": metadata,
                "page_count": len(pdf.pages),
                "status": "success",
                "extracted_json": extracted_json
            }
            
            logger.info(f"Successfully processed file. Metadata: {json.dumps(metadata, indent=4)}")
            return response
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}") 