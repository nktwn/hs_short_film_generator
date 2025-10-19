
FROM python:3.13-slim


WORKDIR /app


COPY ./requirements.txt .


RUN pip install --no-cache-dir --upgrade -r requirements.txt


COPY . /app


CMD ["uvicorn", "main:app", "--reload", "--port", "8000", "--host", "0.0.0.0"]