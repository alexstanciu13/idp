FROM python:3.8

WORKDIR /io-service

COPY io-service/requirements.txt /io-service/
RUN pip install -r requirements.txt

ADD io-service/*.py /io-service/

EXPOSE 5001

CMD ["python3", "-u", "/io-service/server.py"]