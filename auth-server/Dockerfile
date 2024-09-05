FROM python:3.8

WORKDIR /auth-server

COPY auth-server/requirements.txt /auth-server/
RUN pip install -r requirements.txt

ADD auth-server/*.py /auth-server/

EXPOSE 6001

CMD ["python3", "-u", "/auth-server/server.py"]