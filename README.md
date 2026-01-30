# Bhavya Health Data Fetcher

Bihar State Health System Performance Data Collection Tool

## Project Structure

```
bhavya_fetcher/
├── backend/
│   └── app.py              # FastAPI backend server
├── frontend/
│   └── index.html          # Web UI
├── .env                    # Environment variables (create from .env.example)
├── .env.example            # Example environment file
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python dependencies
├── start.bat               # One-click starter (Windows)
└── README.md               # This file
```

## Quick Start

### 1. Setup Environment Variables

```bash
# Copy example env file
copy .env.example .env

# Edit .env with your credentials
notepad .env
```

### 2. Run the Application

**Windows:** Double-click `start.bat`

**Manual:**
```bash
# Install dependencies
pip install -r requirements.txt

# Start backend
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000

# Open frontend/index.html in browser
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DB_HOST` | MySQL database host |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `DB_NAME` | Database name |
| `API_BASE_URL` | Bhavya API base URL |
| `API_SECRET_KEY` | API secret key |
| `API_CLIENT_KEY` | API client key |
| `SERVER_HOST` | Server host (default: 127.0.0.1) |
| `SERVER_PORT` | Server port (default: 8000) |

## Features

- **Fetch Today's Data**: One-click fetch for current date
- **Fetch Date Range**: Select custom date range
- **Real-time Progress**: Live updates via Server-Sent Events
- **34 API Endpoints**: All health system data points
- **Duplicate Prevention**: Skips dates already in database
- **Activity Logging**: Detailed logs of all operations

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Database status & record count |
| `/api/endpoints` | GET | List all 34 API endpoints |
| `/api/fetch/today` | GET | Fetch today's data (SSE) |
| `/api/fetch/range` | POST | Fetch date range (SSE) |

## Database

- **Table**: `bhavya_health_data`
- **Columns**: 57 (all TEXT type)
- **Unique Key**: `data_date`

## Deployment

1. Clone the repository
2. Create `.env` file from `.env.example`
3. Configure your database credentials
4. Install dependencies: `pip install -r requirements.txt`
5. Run: `uvicorn backend.app:app --host 0.0.0.0 --port 8000`

## Data Format

All data is saved with "Not Available" for missing values:

| Column | Description |
|--------|-------------|
| data_date | Date for which data was fetched |
| state_name | Bihar |
| year, month | Extracted from date (Month in proper case) |
| number_of_doctors | Staff count |
| ... | 50+ more columns |
| fetched_at | Timestamp |
