# Use official Python image as base
FROM python:3.11

# Set the working directory
WORKDIR /app

# Copy all files to the container
COPY . .

# Install dependencies
RUN pip install flask slack-sdk flask-sqlalchemy

# Expose port 5000
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]
