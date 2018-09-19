Configs for Redis with modules and Sentinel
===========================================

Useful reference, deployment of multi-node Redis in K8S: https://github.com/kubernetes/examples/tree/master/staging/storage/redis

* `redisearch/`

  Docker file for building redisearch.so:
  Why is it needed? Alpine (latest 3.8), CentOS (latest CentOS 7), Debian (latest 9 Stretch) do not contain RediSearch packages.
  The only distribution is Ubuntu 18.04, which does contain the package.

  I was not able to compile the module on Alpine 3.8 due to compilation error. The most probable that this is due to musl glibc version in Alpines (vs. "standard" glibc).
  On Ubuntu 16.04/18.04 it compiled without any error, but the existing tests failed (66% of all the tests failed), maybe due to an unobvious dependency.
  The only successful environment was a Debian 9 -based image from redislabsmodules (see https://github.com/RedisLabsModules/RediSearch/blob/master/Dockerfile, https://hub.docker.com/r/redislabs/redismod/~/dockerfile/). Image size ~625MB.

  Quick start guide: https://oss.redislabs.com/redisearch/Quick\_Start/

* `docker_runner/`

  Dockerfile for running Redis Server v4 with loaded module. Redis configuration for master and slave should contain `aof-use-rdb-preamble yes` (see https://github.com/RedisLabsModules/RediSearch/issues/290).
  The images can be Debian 9 from official redis repository (image size ~90MB) or Ubuntu 18.04 (image size ~130MB).

So, for Ubuntu 18.04 (LTS) distribution, building redisearch module is not required, as it is already available in `redis-redisearch` package.

Commands
--------

* `docker build -t redisearch-ubuntu -f ubuntu.Dockerfile .`

* Local docker image with minikube: https://stackoverflow.com/questions/42564058/how-to-use-local-docker-images-with-minikube

  `eval $(minikube docker-env)`
  You have to run eval on each terminal you want to use, since it only sets the environment variables for the current shell session.

* Interact with a container:
  `kubectl exec redis-rgldw -i -t bash`

