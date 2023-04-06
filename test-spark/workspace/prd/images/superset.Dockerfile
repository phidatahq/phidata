FROM phidata/superset:2.0.1

RUN pip install --upgrade pip

COPY workspace/prd/superset/resources/requirements-superset.txt /
RUN pip install -r /requirements-superset.txt

COPY workspace/prd/superset/resources /app/docker/
