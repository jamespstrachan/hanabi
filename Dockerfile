FROM python:3.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    vim \
    expect \
    screen \
    && rm -rf /var/lib/apt/lists/*

RUN echo "defshell -bash" >> ~/.screenrc

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .


CMD ["bash"]
