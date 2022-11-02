FROM phidata/python:3.9.12
LABEL maintainer="Ashpreet Bedi <ashpreet@phidata.com>"

ARG PHIDATA_DIR=/phidata
COPY . ${PHIDATA_DIR}
RUN pip3 install --editable ${PHIDATA_DIR}
