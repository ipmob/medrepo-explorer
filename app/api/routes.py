import os
import json
import re
from typing import Dict, Any

import httpx
import pdfplumber
from fastapi import APIRouter, UploadFile, File, HTTPException
import io
from app.utils.logger import logger
from app.api.models.schema_models import MedicalReport, TestResults
from app.api.prompts.lab_report_extractor_system_prompt import SYSTEM_PROMPT as LAB_REPORT_EXTRACTOR_SYSTEM_PROMPT
from app.api.prompts.extraction_tool_call_gemini import TOOL_CALL_GEMINI as EXTRACTION_TOOL_SCHEMA
from app.api.loinc_endpoints import router as loinc_router
from app.loinc.loinc_mapper import get_loinc_mapper

# Main router that combines all sub-routers
router = APIRouter()

# Include LOINC router for LOINC code mapping
router.include_router(loinc_router, prefix="/loinc", tags=["loinc"])

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL_NAME="google/gemini-2.0-pro-exp-02-05:free"

# Load tool schema for function calling
TOOL_SCHEMA = EXTRACTION_TOOL_SCHEMA

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
                    "model": OPENROUTER_MODEL_NAME,
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

            logger.info(f"Raw json form model {OPENROUTER_MODEL_NAME} :  {content}")
            
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

                # logger.info(f"Generated json form model {OPENROUTER_MODEL_NAME} : {json.dumps(json_obj, indent=4)}")
                # clean json object
                if isinstance(json_obj, dict) and 'content' in json_obj:
                    content_str = json_obj['content']
                    # Try to extract JSON from content if it contains JSON code blocks
                    json_pattern = r"```json\s*([\s\S]*?)\s*```"
                    json_match = re.search(json_pattern, content_str)
                    if json_match:
                        try:
                            extracted_json = json.loads(json_match.group(1))
                            json_obj = extracted_json
                            logger.info("Successfully extracted and parsed JSON from content")
                        except json.JSONDecodeError:
                            logger.warning("Found JSON code block but couldn't parse it")
                            
                logger.info(f"Generated json form model {OPENROUTER_MODEL_NAME} : {json.dumps(json_obj, indent=4)}")
                return json_obj
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {str(e)}")
                raise HTTPException(status_code=500, detail="Invalid response format")
                
    except Exception as e:
        logger.error(f"Error calling OpenRouter API: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating summary")
    

# async def generate_report_extraction(text: str) -> Dict[str, Any]:
#     """
#     Extract standardized medical report data using OpenRouter AI with function calling
#     """
#     headers = {
#         "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#         "HTTP-Referer": "https://your-site.com",
#         "Content-Type": "application/json"
#     }
    
#     try:
#         async with httpx.AsyncClient() as client:
#             logger.info(f"Extracting medical report data with OpenRouter API")
#             response = await client.post(
#                 OPENROUTER_URL,
#                 headers=headers,
#                 json={
#                     "model": OPENROUTER_MODEL_NAME,
#                     "messages": [
#                         {"role": "system", "content": LAB_REPORT_EXTRACTOR_SYSTEM_PROMPT},
#                         {"role": "user", "content": f"Extract structured information from this medical report: \n\n{text}"}
#                     ],
#                     "tools": [{
#                         "type": "function",
#                         "function": TOOL_SCHEMA["tools"][0]["function_declarations"][0]
#                     }],
#                     "tool_choice": {
#                         "type": "function",
#                         "function": {"name": "extract_medical_report"}
#                     }
#                 }
#             )
            
#             if response.status_code != 200:
#                 logger.error(f"OpenRouter API error: {response.text}")
#                 raise HTTPException(status_code=500, detail="Error extracting report data")
            
#             result = response.json()
#             logger.info(f"RAW response from {OPENROUTER_MODEL_NAME}: {json.dumps(result, indent=4)}")
            
#             # Handle Gemini-style function calling response
#             if "choices" in result and result["choices"]:
#                 choice = result["choices"][0]
#                 message = choice.get("message", {})
                
#                 # Check for function call in the response
#                 if "tool_calls" in message:
#                     tool_call = message["tool_calls"][0]  # Get the first tool call
#                     if tool_call["function"]["name"] == "extract_medical_report":
#                         try:
#                             extracted_data = json.loads(tool_call["function"]["arguments"])
#                             logger.info(f"Successfully extracted data: {json.dumps(extracted_data, indent=4)}")
                            
#                             # Validate the extracted data
#                             try:
#                                 report = MedicalReport(**extracted_data)
#                                 logger.info("Successfully validated medical report data")
#                             except Exception as e:
#                                 logger.warning(f"Validation warning for extracted data: {str(e)}")
                            
#                             return extracted_data
                            
#                         except json.JSONDecodeError as e:
#                             logger.error(f"Error parsing function arguments: {str(e)}")
#                             raise HTTPException(status_code=500, detail="Invalid function response format")
                
#                 # Fallback to content parsing if no tool calls found
#                 content = message.get("content", "")
#                 if content:
#                     logger.info("No tool calls found, attempting to parse content")
#                     try:
#                         # Try to extract JSON from content
#                         json_pattern = r"```json\s*([\s\S]*?)\s*```"
#                         json_match = re.search(json_pattern, content)
#                         if json_match:
#                             extracted_json = json.loads(json_match.group(1))
#                             logger.info("Successfully extracted JSON from content")
#                             return extracted_json
#                     except Exception as e:
#                         logger.error(f"Error extracting JSON from content: {str(e)}")
#                         raise HTTPException(status_code=500, detail="Failed to extract structured data")
            
#             logger.error("No valid response structure found")
#             raise HTTPException(status_code=500, detail="Invalid response format from API")
                
#     except Exception as e:
#         logger.error(f"Error calling OpenRouter API: {str(e)}")
#         raise HTTPException(status_code=500, detail="Error generating extraction")

async def generate_report_extraction(text: str) -> Dict[str, Any]:
    """
    Extract standardized medical report data using OpenRouter AI with function calling
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://your-site.com",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Extracting medical report data with OpenRouter API")
            response = await client.post(
                OPENROUTER_URL,
                headers=headers,
                json={
                    "model": OPENROUTER_MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": LAB_REPORT_EXTRACTOR_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Extract structured information from this medical report: \n\n{text}"}
                    ],
                    "tools": [{
                        "type": "function",
                        "function": TOOL_SCHEMA["tools"][0]["function_declarations"][0]
                    }],
                    "tool_choice": {
                        "type": "function",
                        "function": {"name": "extract_medical_report"}
                    }
                }
            )
            
            if response.status_code != 200:
                logger.error(f"OpenRouter API error: {response.text}")
                raise HTTPException(status_code=500, detail="Error extracting report data")
            
            result = response.json()
            logger.info(f"RAW response from {OPENROUTER_MODEL_NAME}: {json.dumps(result, indent=4)}")
            
            # Handle Gemini-style function calling response
            if "choices" in result and result["choices"]:
                choice = result["choices"][0]
                message = choice.get("message", {})
                
                # Check for function call in the response
                if "tool_calls" in message:
                    tool_call = message["tool_calls"][0]  # Get the first tool call
                    if tool_call["function"]["name"] == "extract_medical_report":
                        try:
                            extracted_data = json.loads(tool_call["function"]["arguments"])
                            logger.info(f"Successfully extracted data: {json.dumps(extracted_data, indent=4)}")
                            
                            # Convert array-based indicators to dictionary format
                            if "test_results" in extracted_data and "indicators" in extracted_data["test_results"]:
                                if isinstance(extracted_data["test_results"]["indicators"], list):
                                    indicators_dict = {}
                                    for indicator in extracted_data["test_results"]["indicators"]:
                                        if "name" in indicator:
                                            name = indicator.pop("name")
                                            indicators_dict[name] = indicator
                                        else:
                                            logger.warning(f"Indicator missing 'name' field: {indicator}")
                                    
                                    # Replace array with dictionary
                                    extracted_data["test_results"]["indicators"] = indicators_dict
                                    logger.info("Converted indicators array to dictionary format")
                            
                            # Validate the extracted data
                            try:
                                report = MedicalReport(**extracted_data)
                                logger.info("Successfully validated medical report data")
                            except Exception as e:
                                logger.warning(f"Validation warning for extracted data: {str(e)}")
                            
                            return extracted_data
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing function arguments: {str(e)}")
                            raise HTTPException(status_code=500, detail="Invalid function response format")
                
                # Fallback to content parsing if no tool calls found
                content = message.get("content", "")
                if content:
                    logger.info("No tool calls found, attempting to parse content")
                    try:
                        # Try to extract JSON from content
                        json_pattern = r"```json\s*([\s\S]*?)\s*```"
                        json_match = re.search(json_pattern, content)
                        if json_match:
                            extracted_json = json.loads(json_match.group(1))
                            
                            # Convert array-based indicators if present in extracted JSON
                            if "test_results" in extracted_json and "indicators" in extracted_json["test_results"]:
                                if isinstance(extracted_json["test_results"]["indicators"], list):
                                    indicators_dict = {}
                                    for indicator in extracted_json["test_results"]["indicators"]:
                                        if "name" in indicator:
                                            name = indicator.pop("name")
                                            indicators_dict[name] = indicator
                                        else:
                                            logger.warning(f"Indicator missing 'name' field: {indicator}")
                                    
                                    # Replace array with dictionary
                                    extracted_json["test_results"]["indicators"] = indicators_dict
                                    logger.info("Converted indicators array to dictionary format in content JSON")
                            
                            logger.info("Successfully extracted JSON from content")
                            return extracted_json
                    except Exception as e:
                        logger.error(f"Error extracting JSON from content: {str(e)}")
                        raise HTTPException(status_code=500, detail="Failed to extract structured data")
            
            logger.error("No valid response structure found")
            raise HTTPException(status_code=500, detail="Invalid response format from API")
                
    except Exception as e:
        logger.error(f"Error calling OpenRouter API: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating extraction")
    

def process_test_results(test_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the test results and return a list of ProcessedTestIndicator
    """
    test_type=test_result["test_results"]["test_type"]
        
    processed_indicators = []
    for indicator in test_result["test_results"]["indicators"]:
        processed_indicators.append(process_indicators(indicator))

    
    insight = process_insights(processed_indicators)
    

    return TestResults(
        test_type=test_type,
        indicators=processed_indicators,
        analysis=insight
    )





def process_insights(indicator: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the insights for each indicator
    """
    return indicator

def process_indicators(indicator: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the indicators for each indicator
    """
    return indicator

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

            # extracted_json = await generate_summary(extracted_text)
            test_result = await generate_report_extraction(extracted_text)

            # convert test_result to ProcessedTestIndicator
            # process_results = process_test_results(test_result)
            
            response = {
                "filename": file.filename,
                "text": extracted_text,
                "metadata": metadata,
                "page_count": len(pdf.pages),
                "status": "success",
                "test_result": test_result,
                # "processed_test_results": process_test_results
            }
            
            logger.info(f"Successfully processed file. Metadata: {json.dumps(metadata, indent=4)}")
            return response
    
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}") 

# Get the global instance (initialized at startup)
mapper = get_loinc_mapper()

# Use the mapper
result = mapper.find_loinc_code("Hemoglobin")