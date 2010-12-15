import random
import sys

from pylons import cache, config
from genshi.template import NewTextTemplate

from ckan.lib.cache import proxy_cache, get_cache_expires
from ckan.lib.base import *
import ckan.lib.stats

cache_expires = get_cache_expires(sys.modules[__name__])

class HomeController(BaseController):
    repo = model.repo

    @proxy_cache(expires=cache_expires)
    def index(self):
        c.package_count = model.Session.query(model.Package).count()
        c.revisions = model.Session.query(model.Revision).limit(10).all()
        if len(c.revisions):
            cache_key = str(hash((c.revisions[0].id, c.user)))
        else:
            cache_key = "fresh-install"
        
        etag_cache(cache_key)
        def tag_counts():
            '''Top 50 tags (by package counts) in random order (to make cloud
            look nice).
            '''
            # More efficient alternative to get working:
            # sql: select tag.name, count(*) from tag join package_tag on tag.id =
            # package_tag.tag_id where pacakge_tag.state = 'active'
            # c.tags = model.Session.query(model.Tag).join('package_tag').order_by(func.count('*')).limit(100)
            tags = model.Session.query(model.Tag).all()
            # we take the name as dbm cache does not like Tag objects - get:
            # Error: can't pickle function objects
            tag_counts = ckan.lib.stats.Stats().top_tags(limit=50,
                                            returned_tag_info='name')
            tag_counts = [ tuple(row) for row in tag_counts ]
            random.shuffle(tag_counts)
            return tag_counts
        mycache = cache.get_cache('tag_counts', type='dbm')
        c.tag_counts = mycache.get_value(key='tag_counts_home_page',
                createfunc=tag_counts, expiretime=cache_expires)
        return render('home/index.html', cache_key=cache_key,
                cache_expire=cache_expires)

    def license(self):
        return render('home/license.html', cache_expire=cache_expires)

    def about(self):
        return render('home/about.html', cache_expire=cache_expires)
        
    def language(self):
        response.content_type = 'text/json'
        return render('home/language.js', cache_expire=cache_expires,
                      method='text', loader_class=NewTextTemplate)

    def cache(self, id):
        '''Manual way to clear the caches'''
        if id == 'clear':
            wui_caches = ['tag_counts', 'search_results', 'stats']
            for cache_name in wui_caches:
                cache_ = cache.get_cache(cache_name, type='dbm')
                cache_.clear()
            return 'Cleared caches: %s' % ', '.join(wui_caches)

