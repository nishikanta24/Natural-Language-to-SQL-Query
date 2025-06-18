# Use official Python base image
FROM python:3.10

# Set working directory inside container
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt


CMD ["streamlit", "run", "app_ui.py"]
#CMD ["tail", "-f", "/dev/null"] 