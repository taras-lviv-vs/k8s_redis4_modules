FROM redislabsmodules/rmbuilder:latest as builder

# Build the source
ADD . /RSBUILD
WORKDIR /RSBUILD
RUN set -ex;\
    rm -rf docker-build; \
    mkdir docker-build; \
    cd docker-build; \
    cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ../; \
    make -j4; \
    pip install git+https://github.com/RedisLabsModules/RLTest.git@master; \
    pip install git+https://github.com/RedisLabs/rmtest@2.0; \
    make test;

# id=$(docker create fed7799a51e2)
# docker cp $id:/RSBUILD/docker-build/redisearch.so redisearch.so
# docker rm -v $id
