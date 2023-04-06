FROM phidata/databox-spark:2.5.1

RUN pip install --upgrade pip

COPY requirements.txt /
RUN pip install -r /requirements.txt

COPY workspace/prd/airflow/resources/requirements-airflow.txt /
RUN pip install -r /requirements-airflow.txt

COPY workspace/prd/airflow/resources/webserver_config.py ${AIRFLOW_HOME}/

# Install python3 kernel for jupyter
RUN ipython kernel install --name "python3"
