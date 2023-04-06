FROM phidata/jupyter-spark:3.5.2

RUN pip install --upgrade pip

COPY requirements.txt /
RUN pip install -r /requirements.txt

COPY workspace/prd/jupyter/resources /usr/local/jupyter
RUN pip install -r /usr/local/jupyter/requirements-jupyter.txt

RUN ln -s /usr/local/jupyter/gitconfig ~/.gitconfig
