FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir --no-deps . && mkdir -p /app/data

# Inside the container the app must listen on all interfaces so a published
# port can reach it. Publish it to loopback only:
#   docker run --rm -p 127.0.0.1:5057:5057 orderbase
ENV ORDERBASE_HOST=0.0.0.0 \
    ORDERBASE_DB=/app/data/orderbase.db \
    ORDERBASE_DEMO_USERS=0

EXPOSE 5057
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5057/health', timeout=2)"
CMD ["orderbase"]
