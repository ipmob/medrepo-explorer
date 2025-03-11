import requests
from typing import Dict, Any

def test_upload(file_path: str) -> Dict[str, Any]:
    """
    Test the PDF upload API endpoint.
    
    Args:
        file_path: Path to the PDF file to upload
        
    Returns:
        The JSON response from the API
    """
    url = "http://localhost:8000/api/upload/"
    files = {"file": open(file_path, "rb")}
    
    try:
        response = requests.post(url, files=files)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        files["file"].close()

if __name__ == "__main__":
    # Replace with the path to your PDF file
    result = test_upload("report.pdf")
    print(result) 