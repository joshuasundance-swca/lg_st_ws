FROM python:3.11-slim-bookworm

RUN adduser --uid 1000 --disabled-password --gecos '' appuser
USER 1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

RUN pip install --user --no-cache-dir --upgrade pip

COPY ./requirements.txt /home/appuser/requirements.txt

RUN pip install --user --no-cache-dir --upgrade \
    -r /home/appuser/requirements.txt

COPY ./lg_st_ws/ /home/appuser/lg_st_ws/
WORKDIR /home/appuser
