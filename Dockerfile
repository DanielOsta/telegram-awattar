FROM alpine:latest as builder
ENV PYTHONUNBUFFERED 1

RUN apk add --update \
      python3 \
      py-pip && \
      python -m venv /opt/venv
# Enable venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements.txt .

RUN pip install --upgrade --requirement requirements.txt

FROM alpine:latest

ARG APP_DIR=/app
ENV PATH="/opt/venv/bin:$PATH"

RUN apk add --update \
      python3 && \
      rm -rf /var/cache/apk/*

COPY --from=builder /opt/venv /opt/venv
RUN mkdir $APP_DIR
WORKDIR $APP_DIR

COPY main.py $APP_DIR

# -u -> force the stdout and stderr streams to be unbuffered
CMD ["python", "-u", "main.py"]
