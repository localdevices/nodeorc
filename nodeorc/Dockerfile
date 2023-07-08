FROM python:3.10-buster

COPY requirements.txt /app/
WORKDIR /app

RUN apt update
RUN apt install ffmpeg libsm6 libxext6 libgl1 -y
RUN pip install --upgrade pip \
    &&  pip install --trusted-host pypi.python.org --requirement requirements.txt

CMD ["python", "-u", "main.py"]
# Use empty entry point to prevent container restarts while developing.
#ENTRYPOINT ["tail", "-f", "/dev/null"]
