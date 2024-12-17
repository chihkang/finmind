# FinMind Stock Price Tracker

A FastAPI-based application that automatically tracks and updates stock prices using the FinMind API. This service provides scheduled updates for both Taiwan and US stock markets, with support for manual triggers and health monitoring.

## Features

- Automated stock price updates for Taiwan and US markets
- Market hours-aware scheduling system
- RESTful API endpoints for health checks and manual updates
- Timezone-aware operations (configured for Taipei time)
- Comprehensive logging system
- Environment-based configuration

## Prerequisites

- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone [your-repository-url]
cd finmind
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv finmind_env
source finmind_env/bin/activate  # On Windows, use: finmind_env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with your configuration:
```env
FINMIND_TOKEN=your_token_here
TZ=Asia/Taipei
HOST=0.0.0.0
PORT=8000
```

## Project Structure

```
finmind/
├── config/         # Configuration settings
├── core/          # Core business logic
│   ├── market.py      # Market hours management
│   ├── scheduler.py   # Job scheduling
│   └── updater.py     # Stock price updates
├── utils/         # Utility functions
├── .env          # Environment variables
├── main.py       # Application entry point
└── requirements.txt
```

## Usage

### Starting the Service

Run the application using:
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

- `GET /`: Health check endpoint
  - Returns current service status and timezone information

- `GET /trigger`: Manual update trigger
  - Manually triggers a stock price update regardless of market hours

### Scheduled Updates

The service automatically schedules updates based on market hours:
- Taiwan Market: During TSE trading hours
- US Market: During NYSE trading hours

## Dependencies

- FastAPI: Web framework
- uvicorn: ASGI server
- FinMind: Stock market data API
- APScheduler: Task scheduling
- pandas: Data manipulation
- python-dotenv: Environment configuration

## Configuration

Key configurations are managed through environment variables:
- `FINMIND_TOKEN`: Your FinMind API token
- `TZ`: Timezone setting (default: Asia/Taipei)
- `HOST`: Server host address
- `PORT`: Server port number

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License

Copyright (c) 2024 Chih Kang Lin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Acknowledgments

- FinMind API for providing stock market data
- FastAPI framework for the web service implementation
