# Expense Tracker MCP -- production image
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py db.py ./

# Environment variables (DATABASE_URL, SERVER_URL, PORT)
# are provided at deploy time by your cloud hosting platform.
EXPOSE 8000
CMD ["python", "server.py"]
