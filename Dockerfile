# Start from a small Linux image that already has Python 3.12 installed.
FROM python:3.12-slim

# Tell Python not to create .pyc bytecode files inside the container.
ENV PYTHONDONTWRITEBYTECODE=1
# Tell Python to print logs right away instead of buffering them.
ENV PYTHONUNBUFFERED=1
# Tell pip not to keep a download cache, which helps keep the image smaller.
ENV PIP_NO_CACHE_DIR=1

# Everything below runs inside /app in the container.
WORKDIR /app

# Copy only the dependency list first so Docker can cache installs between builds.
COPY requirements.txt .
# Install Python dependencies into the image.
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the app code into the container.
COPY . .

# Document that Streamlit listens on port 8501.
EXPOSE 8501

# Start the Streamlit app and bind it to all network interfaces in the container.
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
