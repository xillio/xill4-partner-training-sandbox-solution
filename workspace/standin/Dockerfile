# A stand-in for the Xill4 image -- see README.md. Not Xill4.
#
# Both build arguments exist for hosts behind a proxy or an air gap:
#   docker build --build-arg BASE=mirror.gcr.io/library/python:3.12-slim \
#                --build-arg DEPS= -t xill4-standin:dev .
# With DEPS empty the stand-in still serves HTTP and writes to the mounted target, but
# cannot reach MongoDB -- so preflight's mongo-state check fails, as it should.
ARG BASE=python:3.12-slim
FROM ${BASE}
ARG DEPS="pymongo==4.8.0"
RUN { [ -z "${DEPS}" ] || pip install --no-cache-dir ${DEPS}; } \
 && useradd --uid 10001 --create-home standin
COPY serve.py /usr/local/bin/serve.py
EXPOSE 8000
USER 10001
CMD ["python", "/usr/local/bin/serve.py"]
