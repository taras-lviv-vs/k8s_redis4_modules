# Package the runner
FROM redis:latest
ENV LIBDIR /usr/lib/redis/modules
WORKDIR /data
RUN set -ex;\
    mkdir -p "$LIBDIR";

COPY redisearch.so /usr/lib/redis/modules/redisearch.so
COPY redis-master.conf /redis-master/redis.conf
COPY redis-slave.conf /redis-slave/redis.conf
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD [ "/run.sh" ]

ENTRYPOINT [ "bash", "-c" ]

