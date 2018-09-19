FROM ubuntu:18.04

RUN apt-get update -y
# Ubuntu 18.04 has Redis 4.0.9
RUN apt-get install -y redis-server redis-sentinel

COPY redisearch.so /usr/lib/redis/modules/redisearch.so
COPY redis-master.conf /redis-master/redis.conf
COPY redis-slave.conf /redis-slave/redis.conf
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD [ "/run.sh" ]

ENTRYPOINT [ "bash", "-c" ]

