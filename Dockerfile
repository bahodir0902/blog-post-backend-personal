FROM python:3.13-slim

LABEL authors="bahodir"

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +777 /app/entrypoint.sh

EXPOSE 8008

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
