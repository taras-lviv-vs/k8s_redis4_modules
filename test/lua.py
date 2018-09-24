import copy
import json
import pprint
import sys

# pip install redisearch
import redisearch

from string import Template

from vidscale.cloudscale.core.lib.db.redis import RedisDatabase

def init_db(db, orgs=100, accounts_per_org=1000):
    key_tmpl = 'account_id:{}:org_id:{}:bigorg'
    json_tmpl = dict(name='default_name',
                     account_id=0,
                     org_id=0)
    account_name_tmpl = 'myaccount_{}'
    account_id = 1
    for org in range(orgs):
        org_id = org + 1
        for account in range(accounts_per_org):
            doc = copy.deepcopy(json_tmpl)
            doc['name'] = account_name_tmpl.format(account_id)
            doc['account_id'] = account_id
            doc['org_id'] = org_id
            db.set(key_tmpl.format(account_id, org_id),
                   json.dumps(doc))

            account_id += 1

    # System exit
    sys.exit(0)

def build_index(db, host, port):
    # build redisearch index
    keys = db.redis.keys('account_id:*')
    if not keys:
        return

    # create index
    client = redisearch.Client('rsIndex', conn=db.redis)
    client.create_index([redisearch.TextField('name', sortable=True)])

    for key in keys:
        doc_string = db.redis.get(key)
        doc = json.loads(doc_string)
        # index the document
        client.add_document('_id:{}'.format(key), name=doc['name'])

def run_rs_query(db, sort_data=True):
    #query = redisearch.Query('myaccount*').verbatim().sort_by('name', asc=False).paging(20, 20)

    client = redisearch.Client('rsIndex', conn=db.redis)
    query = redisearch.Query('myaccount').verbatim().in_order()
    if sort_data:
        query = query.sort_by('name', asc=True)
    query = query.paging(20, 20)
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
            return elem1:match('"name": "%a+_%d+"') > elem2:match('"name": "%a+_%d+"')
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
            if res:match('"name": "my%a+_%d+"') then
                table.insert(filtered_results, res)
            end;
        end;

        -- OFFSET and LIMIT;
        return cs.slice(filtered_results, 20, 20)
        """

    template_obj = Template(template_string)
    if sort_data:
        script = template_obj.substitute(sortComment='')
    else:
        script = template_obj.substitute(sortComment='--')

    results = db.redis.eval(script, numkeys=0)
    return results

if __name__ == '__main__':

    #from redis.sentinel import Sentinel
    #sentinel = Sentinel([('192.168.64.2', 30001)], socket_timeout=0.1)
    #master_host, master_port = sentinel.discover_master('mymaster')

    master_host, master_port = ('192.168.64.2', 30542)
    redis_conf = dict(host=master_host, port=master_port, db=0)
    db = RedisDatabase(redis_conf)
    #init_db(db.redis)

    #pprint.pprint('lua:')
    #results = run_lua(db, sort_data=True)
    #pprint.pprint(results)

    pprint.pprint('redisearch:')
    #build_index(db, master_host, master_port)
    results = run_rs_query(db, sort_data=True)
    pprint.pprint(results)


