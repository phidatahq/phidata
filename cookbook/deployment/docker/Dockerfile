# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Define environment variable
ENV DB_URL=postgresql+psycopg2://ai:ai@pgvector:5432/ai

# Run app.py when the container launches
CMD ["python", "assistant.py"]
