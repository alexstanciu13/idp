FROM python:3.8

WORKDIR /business-service

COPY business-service/requirements.txt /business-service/
RUN pip install -r requirements.txt

ADD business-service/*.py /business-service/

EXPOSE 4107

CMD ["python3", "-u", "/business-service/server.py"]