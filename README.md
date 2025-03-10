# Medical Report Explorer

A web application for uploading and parsing medical reports in PDF format.

## Project Structure

```
med-repo-explorer/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── frontend/
│   ├── static/
│   ├── templates/
│   ├── __init__.py
│   └── main.py
├── requirements.txt
├── test_api.py
└── README.md
```

## Setup

1. Create a virtual environment:
   ```
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - On Windows:
     ```
     .venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source .venv/bin/activate
     ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

Start the FastAPI server:
```
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000.

## API Endpoints

- `POST /api/upload/`: Upload a PDF file and get the extracted text and metadata.

## Testing

You can test the API using the provided test script:
```
python test_api.py
```

Make sure to place a PDF file named `medical_report.pdf` in the project root directory, or modify the script to point to your PDF file. 


python -m app.main
/docs