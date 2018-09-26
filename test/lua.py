import copy
import json
import pprint
import sys
import time

# pip install redisearch
import redisearch

from string import Template

from vidscale.cloudscale.core.lib.db.redis import RedisDatabase


def init_db(db, orgs=100, accounts_per_org=1000):
    key_tmpl = 'account_id:{}:org_id:{}:bigorg'
    json_tmpl = dict(name='default_name',
                     account_id=0,
                     org_id=0)
    account_name_tmpl = 'myaccount {}'
    account_id = 1
    for org in range(orgs):
        org_id = org + 1
        for account in range(accounts_per_org):
            doc = copy.deepcopy(json_tmpl)
            doc['name'] = account_name_tmpl.format(account_id)
            doc['desc'] = account_name_tmpl.format(account_id)
            doc['info'] = account_name_tmpl.format(account_id)
            doc['account_id'] = account_id
            doc['org_id'] = org_id
            db.set(key_tmpl.format(account_id, org_id),
                   json.dumps(doc))

            account_id += 1

    return


def build_index(db, host, port):
    # build redisearch index
    keys = db.redis.keys('account_id:*')
    if not keys:
        return

    # create index
    client = redisearch.Client('rsIndex', conn=db.redis)
    client.create_index([redisearch.TextField('name_sortable', sortable=True),
                         redisearch.TextField('desc_unsortable', sortable=False),
                         redisearch.TextField('info_nostem', no_stem=True)])

    for key in keys:
        doc_string = db.redis.get(key)
        doc = json.loads(doc_string)
        # index the document
        client.add_document('_id:{}'.format(key),
                            name_sortable=doc['name'],
                            desc_unsortable=doc['desc'],
                            info_nostem=doc['info'])

def run_rs_query(db, sort_data=True):
    #client.search(redisearch.Query('@name_sortable:myaccount').sort_by('name_sortable', asc=True).paging(0, 20)).docs

    client = redisearch.Client('rsIndex', conn=db.redis)
    query = redisearch.Query('@name_sortable:myaccount')
    if sort_data:
        query = query.sort_by('name_sortable', asc=False)
    query = query.paging(20, 10)
    res = client.search(query)

    keys = []
    for doc in res.docs:
        key = doc.id.lstrip('_id:')
        keys.append(key)

    docs = []
    if keys:
        docs = db.redis.mget(keys)
    return docs

def run_lua(db, sort_data=True):
    template_string = \
        """
        -- function for paging;
        local cs = {}
        function cs.slice(tbl, offset, page_size)
            local sliced = {}
            for i = offset,offset + page_size - 1 do
               table.insert(sliced, tbl[i])
            end
            return sliced
        end;

        -- function to define sorting by field;
        function cs.compare(elem1, elem2)
            return elem1:match('"name": "[%a%d ]+"') > elem2:match('"name": "[%a%d ]+"')
            -- < ASC
            -- > DESC
        end;

        -- Get all resources filtered by fields in "key";
        local keys = redis.call('KEYS', 'account_id:*');
        local results = {};
        for i, key in pairs(keys) do
            local res = redis.call('GET', key)
            table.insert(results, res)
        end;

        -- Sorting takes ~60-70% of the whole execution time;
        -- Compare 40s vs 18s on 100k documents
        ${sortComment}table.sort(results, cs.compare)

        -- Filter by internal fields;
        local filtered_results = {};
        for i, res in pairs(results) do
            if res:match('"name": "my%a+ %d+"') then
                table.insert(filtered_results, res)
            end;
        end;

        -- OFFSET and LIMIT;
        return cs.slice(filtered_results, 21, 10)
        """

    template_obj = Template(template_string)
    if sort_data:
        script = template_obj.substitute(sortComment='')
    else:
        script = template_obj.substitute(sortComment='--')

    results = db.redis.eval(script, numkeys=0)
    return results

def run_lua_with_json(db, sort_data=True):
    template_string = \
        """
        -- function for paging;
        local cs = {}
        function cs.slice(tbl, offset, page_size)
            local sliced = {}
            for i = offset,offset + page_size - 1 do
               table.insert(sliced, tbl[i])
            end
            return sliced
        end;

        -- function to define sorting by field;
        function cs.compare(elem1, elem2)
            return elem1['name']:match('[%a%d ]+') > elem2['name']:match('[%a%d ]+')
            -- < ASC
            -- > DESC
        end;

        -- Get all resources filtered by fields in "key";
        local keys = redis.call('KEYS', 'account_id:*');
        local results = {};
        for i, key in pairs(keys) do
            local res = redis.call('GET', key)
            local val = cjson.decode(res)
            -- Filter by internal fields;
            if string.match(val["name"], "myaccount %d+") then
                table.insert(results, val)
            end;
        end;

        -- Sorting takes ??? of the whole execution time;
        ${sortComment}table.sort(results, cs.compare)

        -- OFFSET and LIMIT;
        local results_slice = cs.slice(results, 21, 10)
        local results_json = {}
        for i, v in pairs(results_slice) do
            table.insert(results_json, cjson.encode(v))
        end;

        return results_json
        """

    template_obj = Template(template_string)
    if sort_data:
        script = template_obj.substitute(sortComment='')
    else:
        script = template_obj.substitute(sortComment='--')

    results = db.redis.eval(script, numkeys=0)
    return results

if __name__ == '__main__':

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--init-db", dest="init_db", action="store_true",
                      help="Init database with data")
    parser.add_option("--build-id", dest="build_id", action="store_true",
                      help="Build redisearch index")
    parser.add_option("--kind", dest="kind",
                      choices=['lua', 'lua_cjson', 'redisearch',],
                      help="Test kind")

    (options, args) = parser.parse_args()

    #from redis.sentinel import Sentinel
    #sentinel = Sentinel([('192.168.64.2', 30001)], socket_timeout=0.1)
    #master_host, master_port = sentinel.discover_master('mymaster')

    master_host, master_port = ('192.168.64.2', 31774)
    redis_conf = dict(host=master_host, port=master_port, db=0)
    db = RedisDatabase(redis_conf)

    if options.init_db:
        pprint.pprint('init db:')
        init_db(db.redis)

    if options.build_id:
        pprint.pprint('build id:')
        build_index(db, master_host, master_port)

    if options.kind == 'lua_cjson':
        t1 = time.time()

        pprint.pprint('lua with cjson:')
        results = run_lua_with_json(db, sort_data=True)
        pprint.pprint(results)
        pprint.pprint('LUA cjson taken {}s'.format(time.time() - t1))

    if options.kind == 'redisearch':
        t2 = time.time()

        pprint.pprint('redisearch:')
        results = run_rs_query(db, sort_data=True)
        pprint.pprint(results)
        pprint.pprint('Redisearch taken {}s'.format(time.time() - t2))

    if options.kind == 'lua':
        t3 = time.time()

        pprint.pprint('lua:')
        results = run_lua(db, sort_data=True)
        pprint.pprint(results)
        pprint.pprint('LUA taken {}s'.format(time.time() - t3))

