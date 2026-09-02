# The grader runs in its own container, never in the trainee's instance: it must be able to
# read the answer key that the trainee cannot.
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY grader/ ./grader/
RUN pip install --no-cache-dir PyYAML boto3

ENV PYTHONPATH=/app/grader PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python", "-m", "grader"]
