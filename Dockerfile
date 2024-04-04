FROM python:3.10-buster

COPY requirements.txt /app/
COPY setup.py /app/
WORKDIR /app

RUN apt update
RUN apt install ffmpeg libsm6 libxext6 libgl1 python3-venv libgdal-dev jq -y
#RUN pip install -e .
RUN pip install --upgrade pip \
    && pip install --trusted-host pypi.python.org --requirement requirements.txt \
    && pip install .

# Get a configuration implemented

# login for LiveORC


# CMD ["nodeorc"]
# CMD ["python", "-u", "main.py"]
# Use empty entry point to prevent container restarts while developing.
#ENTRYPOINT ["tail", "-f", "/dev/null"]
