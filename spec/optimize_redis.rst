===================
Redis Optimizations
===================

TODO
====
- Store a string or a hashmap?

Limitations
===========
- This specification does not consider optimizations at the level of creating resources, e.g. removing Cerberus-based validation of each resource after reading JSON string from Redis and deserializing it;
- This specification does not describe asynchronous replication, using e.g. `Sentinel <https://redis.io/topics/sentinel>`_ master-slave with automatic election of the leader during failover scenario;

Approaches
==========

Overview
--------
Documents are stored as serialized JSON strings at specific keys.  CloudScale applications would GET the entire JSON string, deserialize it, manipulate it, re-serialize and SET it again at the application. This is an anti-pattern.

See `JSON storage<https://redislabs.com/redis-best-practices/data-storage-patterns/json-storage/>`_

Method 1
""""""""
LUA and cjson. Example of approach is here: https://github.com/RedisLabsModules/rejson/blob/master/benchmarks/lua/json-get-path.lua


Pros:

- XXX

Cons:

- XXX

Method 2
""""""""
Redis 4.0+ have the ability to use modules in the form of binary shared objects (\*.so). Shared objects are loaded into Redis process during initialization and their logic is available immediately after Redis is started.

Let's consider `ReJSON <https://github.com/RedisLabsModules/rejson>`_
Intro page: https://oss.redislabs.com/rejson/
The list of commands that exposes ReJSON: https://oss.redislabs.com/rejson/commands/
ReJSON does not support complex query logic: `does rejson in redis support complex get query?<https://stackoverflow.com/questions/47518725/does-rejson-in-redis-support-complex-get-query>`_

Current Redis version is:
::
        $ redis-server -v
        Redis server v=3.2.3 sha=00000000:0 malloc=jemalloc-3.6.0 bits=64 build=cd30fb367b05f482

Pros:

- Allows to update JSON string as a single operation, i.e. no need to GET the whole document, update it in Python, and SET it back in Redis
- Supports `JsonPath <http://goessner.net/articles/JsonPath/>`_.

Cons:

- Is too simple. There is no benefit of using it in CloudScale.
- I'd compare this approach to full table scan when it goes about filter+sort+limit+offset. Quite ineffective operation.

Method 3
""""""""
Modify existing keys in Redis to include index field (field to filter by) into key.

Pros:

- Speed of queries will increase

Cons:

- Need to track queries. Only certain queries can be fast. Request for filtering by a new index field should be discussed.
- Require DB migration (modify keys)
- Inflexible approach due to limited number of index fields, possible with this method.

Secondary Index
---------------
What is secondary index? https://redis.io/topics/indexes
Natively, Redis only offers *primary key access*.
`MySQL vs. Redis<https://db-engines.com/en/system/MySQL%3BRedis>`_ has a note on `RediSearch module<https://oss.redislabs.com/redisearch/>`_ for Secondary Index.

RediSearch module
"""""""""""""""""
`Python client<https://github.com/RedisLabs/redisearch-py>`_
Youtube video from creator of ReJSON `RedisConf17 Deploying the RediSearch Module at Scale & an Intro to the ReJSON module - Itamar Haber<https://www.youtube.com/watch?v=MDnHFWTxDPQ>`_
`RedisConf17 Slides<https://www.slideshare.net/RedisLabs/redisconf17-searching-billions-of-documents-with-redis>`_

This module (and modules overall) require a Redis 4 build.

N.B.: On timeout, the default behavior is that redisearch return its best effort. (Default timeout is 500ms, see https://oss.redislabs.com/redisearch/Configuring/)

Alpine
''''''
Failed to compile RediSearch module on Alpine 3.8: CC compiler errors.
Redis 4 is available from Alpine 3.7.

CentOS
''''''
Able to compile RediSearch module on CentOS 7.
Redis 4 is not available on CentOS 7. Maximum available version from EPEL http://epel.mirror.omnilance.com/7/x86_64/Packages/r/: 3.2.12.
Redis 4 should be compiled from the source code.

Ubuntu
''''''
Ubuntu 16.04, 18.04: 33% tests passed, 57 tests failed out of 85

Debian
''''''
Debian 8, 9: 33% tests passed

RedisLabs's Debian 9 image redislabsmodules/rmbuilder:
::

        FROM redislabsmodules/rmbuilder:latest as builder
        <build steps>

100% tests passed.

This require 2 dockerfiles for building:

1) redislabsmodules/rmbuilder for building redisearch.so. This produces ~625MB image;
2) Debian 9 or Ubuntu 18.04 (redis server v. 4.0.9) for production environment;


# EOF

Transactions
------------
For transactions support and pipelining: https://github.com/RedisLabs/redis-py
CloudScale should do read-update-write in transactions.

String or HashMap?
------------------
TBD

Performance Evaluation
----------------------
Experiments:
 - LUA from Vitaliy Y.
 - LUA + cjson
 - RediSearch

Redisearch
""""""""""
TODO: performance test should include heavy write/read test, to make sure index rebuilding does not break things down.

Create Index
''''''''''''

Easy formula:
::
        Adding one index adds number of index records equal to the number of data records, so when adding all records takes X time, creating one index takes X time.
        Creating 2 indexes takes 2*X time, 3 indexes takes 3*X time:

        (ve3.6mac) ➜  cloudscale git:(develop) ✗ time python perf/lua.py --init-db
        'init db:'
        python perf/lua.py --init-db  9.25s user 2.50s system 7% cpu 2:36.61 total
        (ve3.6mac) ➜  cloudscale git:(develop) ✗ time python perf/lua.py --build-id
        'build id:'
        python perf/lua.py --build-id  18.66s user 5.19s system 5% cpu 7:35.10 total

Command
''''''

Run 100 requests in 10 parallel jobs:

::
        time seq 100 | parallel -j10 'echo {}; time python perf/lua.py --kind=redisearch'

