# How to Run and Test the Message Search Engine API

## Prerequisites
- Python 3.11 or higher installed
- pip package manager

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

Or if you have multiple Python versions:
```bash
python -m pip install -r requirements.txt
```

## Step 2: Run the Application

### Option A: Using Python directly
```bash
python main.py
```

### Option B: Using uvicorn directly (recommended)
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag enables auto-reload on code changes (useful for development).

## Step 3: Verify Server is Running

You should see output like:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Step 4: Test the API

### Method 1: Interactive API Documentation (Swagger UI)

FastAPI automatically provides interactive API documentation:

1. Open your browser and go to: **http://localhost:8000/docs**
2. You'll see a Swagger UI interface with all available endpoints
3. Click on `/search` endpoint
4. Click "Try it out"
5. Enter your search query (e.g., `q=paris`)
6. Set `page=1` and `page_size=20`
7. Click "Execute"
8. View the response below

### Method 2: Alternative API Documentation (ReDoc)

Open: **http://localhost:8000/redoc**

This provides a cleaner, alternative documentation interface.

### Method 3: Using PowerShell/Command Line

#### Test Health Endpoint:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

#### Test Root Endpoint:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/"
```

#### Test Search Endpoint:
```powershell
# Search for "paris"
Invoke-RestMethod -Uri "http://localhost:8000/search?q=paris&page=1&page_size=5"

# Search for "dinner"
Invoke-RestMethod -Uri "http://localhost:8000/search?q=dinner&page=1&page_size=10"

# Search for "opera"
Invoke-RestMethod -Uri "http://localhost:8000/search?q=opera&page=1&page_size=20"
```

### Method 4: Using curl (if available)

```bash
# Health check
curl http://localhost:8000/health

# Root endpoint
curl http://localhost:8000/

# Search endpoint
curl "http://localhost:8000/search?q=paris&page=1&page_size=5"
```

### Method 5: Using Python requests

Create a test script `test_api.py`:
```python
import requests

# Test health endpoint
response = requests.get("http://localhost:8000/health")
print("Health:", response.json())

# Test search endpoint
response = requests.get("http://localhost:8000/search", params={
    "q": "paris",
    "page": 1,
    "page_size": 5
})
data = response.json()
print(f"\nSearch Results for 'paris':")
print(f"Total matches: {data['total']}")
print(f"Response time: {data['response_time_ms']} ms")
print(f"Items returned: {len(data['items'])}")
if data['items']:
    print(f"\nFirst result:")
    print(f"  User: {data['items'][0]['user_name']}")
    print(f"  Message: {data['items'][0]['message']}")
```

Run it:
```bash
python test_api.py
```

## Expected Response Format

### Search Endpoint Response:
```json
{
  "total": 15,
  "items": [
    {
      "id": "b1e9bb83-18be-4b90-bbb8-83b7428e8e21",
      "user_id": "cd3a350e-dbd2-408f-afa0-16a072f56d23",
      "user_name": "Sophia Al-Farsi",
      "timestamp": "2025-05-05T07:47:20.159073+00:00",
      "message": "Please book a private jet to Paris for this Friday."
    }
  ],
  "page": 1,
  "page_size": 20,
  "query": "paris",
  "response_time_ms": 45.23
}
```

## Performance Notes

⚠️ **Important**: The first search request may take 10-30 seconds because:
- It needs to fetch all ~3,349 messages from the external API
- Data is then cached in memory for 60 seconds

✅ **Subsequent requests** (within 60 seconds) should be **<100ms** due to caching.

## Troubleshooting

### Port Already in Use
If port 8000 is already in use, change it:
```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```
Then access at: http://localhost:8001

### Module Not Found Errors
Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Connection Refused
- Make sure the server is running
- Check that you're using the correct port
- Verify firewall settings aren't blocking the connection

## Stop the Server

Press `CTRL+C` in the terminal where the server is running.

