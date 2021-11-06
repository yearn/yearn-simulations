FROM python:3.8


# Install linux dependencies
RUN apt-get update && apt-get install -y libssl-dev npm && \
    rm -rf /var/lib/apt/lists/*

RUN npm install -g ganache-cli

COPY requirements.txt .

RUN pip install -U pip && \
    pip install -r requirements.txt && \
    pip cache purge

# Set up code directory
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY . /usr/src/app/

ENV BROWNIE_PATH="/usr/local/bin/brownie"
ENV DOCKER=true
ENV ENVIRONMENT="dev"

CMD [ "python", "bot/bot_poller.py" ]

