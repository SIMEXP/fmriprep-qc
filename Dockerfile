FROM python:3.7-slim-buster

LABEL maintainer="Loic Tetrel <loic.tetrel.pro@gmail.com>"

# repository
RUN mkdir /fmriprep-qc
RUN mkdir /input
WORKDIR /fmriprep-qc
COPY . /fmriprep-qc

# python dependencies
RUN python3 -m pip install --upgrade pip && python3 -m pip install --no-cache -r requirements.txt

EXPOSE 8050

ENTRYPOINT ["python3", "/fmriprep-qc/fmriprep-qc/main.py", "/input"]