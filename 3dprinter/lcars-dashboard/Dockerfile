FROM python:3.11-slim

WORKDIR /app

# flashforge-python-api drives the printer (HTTP 8898 + TCP 8899);
# numpy + pillow power the Replicator Preview STL->GIF renderer
RUN pip install --no-cache-dir \
    flashforge-python-api==1.4.0 \
    numpy \
    pillow

COPY server.py preview.py index.html comms.html comms.js ./

ENV PORT=8890
EXPOSE 8890

CMD ["python", "server.py"]
