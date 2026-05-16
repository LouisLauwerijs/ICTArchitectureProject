FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY client.py .
ENV WS_URL=ws://ws-server:8765
CMD ["python", "client.py"]
