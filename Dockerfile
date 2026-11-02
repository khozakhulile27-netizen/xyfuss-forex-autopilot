FROM python:3.12-slim

WORKDIR /opt/xyfuss
COPY requirements.txt pyproject.toml README.md ./
COPY xyfuss_forex_autopilot ./xyfuss_forex_autopilot
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
USER nobody
CMD ["python", "-m", "xyfuss_forex_autopilot", "dashboard", "--host", "0.0.0.0", "--port", "8000"]
