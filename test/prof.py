
import json
import time
import pprint

from memory_profiler import profile

from vidscale.cloudscale.core.lib.db.redis import RedisDatabase
from vidscale.cloudscale.core.lib.db.redis.collection import RedisCollection, RedisKeyBuilder
from vidscale.cloudscale.core.lib.paginator import paginate


ACCOUNT_ID_KEY = 'account_id'
ORG_ID_KEY = 'org_id'


class RedisKeyBuilder2(RedisKeyBuilder):

    """
    account_id:39620:org_id:40:bigorg
    """

    def get_key_elements(self, **kwargs):

        key_elements = [ACCOUNT_ID_KEY, kwargs.get(ACCOUNT_ID_KEY, '*'),
                        ORG_ID_KEY, kwargs.get(ORG_ID_KEY, '*'),
                        'bigorg']
        return key_elements


class RedisCollection2(RedisCollection):
    redis_key_builder_class = RedisKeyBuilder2

    def get_resources_with_mget(self, **kwargs):

        redis_docs = []
        redis_keys = self.redis_key_builder.resolve_keys(**kwargs)
        if redis_keys:
            redis_docs = self.db.redis.mget(redis_keys)

        result = []
        for doc in redis_docs:
            result.append(json.loads(doc))
        return result


def _list_resources_lua(db_collection, **kwargs):
    """
    Redis Lua implementation
    """

    result = []
    for _, resource in db_collection.get_key_resource_pairs():
        result.append(resource)
    return result

@paginate
def list_resources_lua(db_collection, **kwargs):
    """
    Redis Lua (paginated)
    """

    return _list_resources_lua(db_collection, **kwargs)

@profile
@paginate
def list_resources_lua_profile(db_collection, **kwargs):
    """
    Redis Lua (paginated, memory profile enabled)
    """

    return _list_resources_lua(db_collection, **kwargs)


@paginate
def list_resources_mget(db_collection, **kwargs):
    """
    Redis MGET (paginated)
    """

    return db_collection.get_resources_with_mget()


@profile
@paginate
def list_resources_mget_profile(db_collection, **kwargs):
    """
    Redis MGET (paginated, memory profile enabled)
    """

    return db_collection.get_resources_with_mget()


if __name__ == '__main__':

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--kind", dest="kind",
                      choices=['lua', 'lua_prof', 'mget', 'mget_prof',],
                      help="Test kind")

    (options, args) = parser.parse_args()

    master_host, master_port = ('192.168.64.2', 32394)
    redis_conf = dict(host=master_host, port=master_port, db=0)
    db = RedisDatabase(redis_conf)

    db_collection = RedisCollection2(db)

    if options.kind == 'lua':
        t1 = time.time()

        pprint.pprint('lua:')
        results = list_resources_lua(db_collection, read_search_params_from_kwargs=True,
                                     sort_by='account_id', offset=100, page_size=20)
        pprint.pprint(results)
        pprint.pprint('LUA taken {}s'.format(time.time() - t1))

    if options.kind == 'lua_prof':
        t2 = time.time()

        pprint.pprint('lua (with memory profiler):')
        results = list_resources_lua_profile(db_collection, read_search_params_from_kwargs=True,
                                             sort_by='account_id', offset=100, page_size=20)
        pprint.pprint(results)
        pprint.pprint('LUA (with memory profiler) taken {}s'.format(time.time() - t2))

    if options.kind == 'mget':
        t3 = time.time()

        pprint.pprint('mget:')
        results = list_resources_mget(db_collection, read_search_params_from_kwargs=True,
                                      sort_by='account_id', offset=100, page_size=20)
        pprint.pprint(results)
        pprint.pprint('MGET taken {}s'.format(time.time() - t3))

    if options.kind == 'mget_prof':
        t4 = time.time()

        pprint.pprint('mget (with memory profiler):')
        results = list_resources_mget_profile(db_collection, read_search_params_from_kwargs=True,
                                              sort_by='account_id', offset=100, page_size=20)
        pprint.pprint(results)
        pprint.pprint('MGET (with memory profiler) taken {}s'.format(time.time() - t4))

