FROM ubuntu:18.04

RUN apt-get update -y
RUN apt-get install -y redis-server redis-sentinel redis-redisearch

COPY redis-master.conf /redis-master/redis.conf
COPY redis-slave.conf /redis-slave/redis.conf
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD [ "/run.sh" ]

ENTRYPOINT [ "bash", "-c" ]

