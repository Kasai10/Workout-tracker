# Use ARM-compatible slim Python image
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8050 for Dash
EXPOSE 8050

# Run the app
CMD ["python", "app.py"]
