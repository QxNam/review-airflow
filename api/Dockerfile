FROM python:3.9.11
WORKDIR /app
COPY . .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt && pip cache purge

CMD ["python", "app.py"]