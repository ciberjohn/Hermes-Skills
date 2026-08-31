FROM python:3.11-slim

WORKDIR /app

# flashforge-python-api drives the printer (HTTP 8898 + TCP 8899)
RUN pip install --no-cache-dir flashforge-python-api==1.4.0

COPY server.py index.html ./

ENV PORT=8890
EXPOSE 8890

CMD ["python", "server.py"]
