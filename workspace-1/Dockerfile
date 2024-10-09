FROM phidata/python:3.11.5

ARG USER=app
ARG APP_DIR=${USER_LOCAL_DIR}/${USER}
ENV APP_DIR=${APP_DIR}
# Add APP_DIR to PYTHONPATH
ENV PYTHONPATH="${APP_DIR}:${PYTHONPATH}"

# Create user and home directory
RUN groupadd -g 61000 ${USER} \
  && useradd -g 61000 -u 61000 -ms /bin/bash -d ${APP_DIR} ${USER}

WORKDIR ${APP_DIR}

# Update pip
RUN pip install --upgrade pip
# Copy pinned requirements
COPY requirements.txt .
# Install pinned requirements
RUN pip install -r requirements.txt

# Copy project files
COPY . .

COPY scripts /scripts
ENTRYPOINT ["/scripts/entrypoint.sh"]
CMD ["chill"]
