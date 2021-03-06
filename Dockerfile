FROM ubuntu:18.04

## Update operating system and install pip
RUN set -xe \
    && apt-get update \
    && apt-get install -y libffi-dev libssl-dev \
    && apt-get install -y python python-dev python-pip \ 
    && apt-get install -y libxft-dev libfreetype6 libfreetype6-dev \
    && apt-get install -y openssh-server
RUN pip install --upgrade pip
RUN pip install pyopenssl ndg-httpsclient pyasn1

# Install python libraries

RUN pip install pandas
RUN pip install sklearn
RUN pip install 'matplotlib==1.4.3'
RUN pip install seaborn
RUN pip install wikipedia
RUN pip install Flask
RUN pip install babel
RUN pip install pyyaml
RUN pip install forex-python
RUN pip install unidecode
RUN pip install tweepy
RUN pip install xgboost
RUN pip install nltk
RUN pip install pyspark
#RUN python -c 'import nltk; nltk.download("all")'

RUN apt-get install -y curl
RUN python -c 'import nltk; nltk.download("stopwords")'
RUN python -c 'import nltk; nltk.download("wordnet")'
RUN python -c 'import nltk; nltk.download("punkt")'

EXPOSE 5000

COPY engine engine
COPY resources resources
COPY flaskr flaskr
COPY startup.sh /startup.sh
COPY cfg.yml cfg.yml

RUN chmod +x /startup.sh
ENTRYPOINT ["/startup.sh","web"]
#CMD bash -C '/startup.sh test';'bash'
