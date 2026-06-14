# LoL Data Pipeline

A Python project for fetching League of Legends data and storing it in a database.

## Setup

### Prerequisites

1. **ODBC Driver**: Install the Microsoft ODBC Driver for SQL Server
   - Download from: [Microsoft ODBC Driver for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
   - Run the installer and install the Visual C++ Redistributable if prompted
   - Restart your terminal/VS Code after installation

2. **Environment Variables**: Create a `.env` file in the project root with:
   ```
   DB_DRIVER=ODBC Driver 17 for SQL Server
   DB_SERVER=your_server
   DB_DATABASE=your_database
   DB_USERNAME=your_username
   DB_PASSWORD=your_password
   RIOT_API_KEY=your_riot_api_key
   ```

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

2. Activate the virtual environment:
   ```bash
   # Windows
   .venv\Scripts\Activate.ps1
   
   # macOS/Linux
   source .venv/bin/activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the main script:
```bash
python main.py
```

## Project Structure

- `main.py` - Main entry point
- `riot_api.py` - Riot API integration
- `database_pipeline.py` - Database operations
- `requirements.txt` - Python dependencies
- `Schema.sql` - Database schema
- `Select.sql` - SQL queries
