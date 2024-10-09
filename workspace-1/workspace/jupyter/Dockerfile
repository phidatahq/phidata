FROM phidata/jupyter:4.0.5

COPY requirements.txt /
RUN pip install -r /requirements.txt

COPY workspace/jupyter/jupyter_requirements.txt /
RUN pip install -r /jupyter_requirements.txt
