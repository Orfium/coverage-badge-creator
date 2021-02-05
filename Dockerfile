FROM python:3-slim

COPY . /app
COPY main.py /main.py
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

CMD ["python", "/main.py"]
