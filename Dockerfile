FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir vkbottle aiohttp python-dotenv mistralai requests

COPY bot.py .

CMD ["python", "bot.py"]