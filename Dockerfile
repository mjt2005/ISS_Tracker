FROM python:3.13

RUN mkdir /app
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY iss_tracker_app.py /app/iss_tracker_app.py
COPY geolocation.py /app/geolocation.py
COPY test_iss_tracker_app.py /app/test_iss_tracker_app

ENTRYPOINT ["python"]
CMD ["iss_tracker_app.py"]