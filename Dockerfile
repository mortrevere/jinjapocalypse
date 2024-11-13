# Use the official Python 3.12 image as the base image
FROM python:3.12

# Set working directory
WORKDIR /jinjapocalypse

# Copy requirements.txt into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container
COPY jinjapocalypse.py .

# Create necessary directories and set permissions
RUN mkdir -p /jinjapocalypse/src /jinjapocalypse/build /jinjapocalypse/media && \
    chown -R nobody:nogroup /jinjapocalypse

# Switch to a non-root user for security purposes
USER nobody

# Set the default command to execute the Python script
ENTRYPOINT ["python", "jinjapocalypse.py"]