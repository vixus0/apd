from flask import request, g, url_for
from peewee import ForeignKeyField
from playhouse.postgres_ext import Match
from math import ceil

from cropdb import app, resources, sub_resources
from cropdb.apd.forms import filter_form
from cropdb.utils import ResponseError, template, select_filter, plural_filter
from cropdb.auth.models import Subscription
from cropdb.auth.decorators import login_required


# - view
#   GET:
#      Return a specific <resource> item identified by <rid>. 
@app.route('/apd/<resource>/get/<rid>')
@login_required
def apd_view(resource, rid):
    if resource not in resources:
        raise ResponseError(404, 'Unknown resource', 'Resource not found.') 

    if g.user.is_admin == False and resource in sub_resources:
        if Subscription.can_access(g.user, resource, rid) == False:
            raise ResponseError(
                    403, 
                    'Not Subscribed', 
                    'You cannot access this '+resource+'.'
                    )

    model = resources[resource]

    try:
        item = model.get(model.keyfield() == rid)
    except model.DoesNotExist:
        raise ResponseError(403, 'Unknown resource', 'Resource not found.') 

    obj = {}
    links = {}

    for prop, field in model._meta.fields.items():
        if isinstance(field, ForeignKeyField):
            rel_resource = field.rel_model.modelname()
            rel_item = getattr(item, prop)

            if rel_item is None:
                continue

            text = rel_item.get_name()
            key = rel_item.get_key()

            links[prop] = url_for('apd_view', resource=rel_resource, rid=key)
            obj[prop] = text
        else:
            obj[prop] = getattr(item, prop)

    backrefs = {}

    for relname, fk in model._meta.reverse_rel.items():
        if g.get('fmt_json'):
            flt_d = dict(field=fk.name, sep=app.config['FLT_SEP'], id=item.id)
            flt = '{field}{sep}eq{sep}{id}'.format(**flt_d)
            backrefs[relname] = url_for('apd_list', 
                    resource=fk.model_class.modelname(), 
                    flt=flt
                    )
        else:
            br = getattr(item, relname)
            backrefs[relname] = br.order_by(br.model_class.orderfield())

    obj['key'] = item.get_key()
    obj['href'] = url_for('apd_view', resource=resource, rid=rid)
    obj['_links'] = links
    obj['_backrefs'] = backrefs

    if 'name' not in obj:
        obj['name'] = item.get_name()

    resource_href = request.referrer

    # For JSON and template
    d = dict(resource=model.modeltitle(), resource_href=resource_href, item=obj)

    # For use in templates
    g.item = item

    return template(resource+'.html', d)


# - list
#   GET:
#       List items of <resource> with pagination.
@app.route('/apd/<resource>/list')
@app.route('/apd/<resource>/list/<int:page>')
@login_required
def apd_list(resource, page=1):
    if resource not in resources:
        raise ResponseError(404, 'Unknown resource', 'Resource not found.') 

    # Get the model that was requested
    model = resources[resource]
    items = model.select()

    # If user isn't admin, and the resource is subscribable, only get items that 
    # user is subscribed to
    if g.user.is_admin == False and resource in sub_resources:
        if Subscription.can_access(g.user, resource, -1) == False:
            idx = Subscription.available_items(g.user, resource)
            
            if idx.count() == 0:
                raise ResponseError(
                        403, 
                        'Not Subscribed: '+plural_filter(resource).title(), 
                        'You are not subscribed to any '+plural_filter(resource)+'.'
                        )

            items = model.select().join(Subscription, on=(Subscription.resource_id == model.keyfield())).where(model.keyfield() << idx)

    # Do initial character filtering
    startsw = request.args.get('sw')

    if startsw:
        if startsw.isalpha():
            startsw = startsw[0]
            swu = startsw.upper()
            swl = startsw.lower()
            items = items.where(model.orderfield().regexp('^[{}{}]'.format(swu,swl)))
        elif startsw == '0':
            items = items.where(model.orderfield().regexp('^[0-9]'))

    # Further filtering based on query string
    and_filters = request.args.getlist('flt') + request.args.getlist('and_flt')
    or_filters = request.args.getlist('or_flt')

    items = select_filter(items, and_filters, or_filters)

    # Filtering inputs
    if hasattr(model, '_filter'):
        ff = filter_form(model, as_json=True)
    else:
        ff = None

    # Pagination
    try:
        per = int(request.args.get('per'))
    except (ValueError, TypeError) as e:
        per = app.config['PER_PAGE']

    count = items.count()
    items = items.order_by(model.orderfield()).paginate(page, per)

    total_pages = int(ceil(count / per))

    if page > 1 and page > total_pages:
        raise ResponseError(404, 'Page not found', 'No such page.')

    if items:
        all_args = {}

        for k,v in request.args.items():
            if k not in ['resource', 'page']:
                all_args[k] = v

        next_page = url_for('apd_list', resource=resource, page=page+1, **all_args)
        prev_page = url_for('apd_list', resource=resource, page=max(1, page-1), **all_args)

        itemlist = []
        
        for item in items:
            key = item.get_key()
            name = item.get_name()
            href = url_for('apd_view', resource=resource, rid=key)

            if 'page' in request.args:
                href = url_for('apd_view', resource=resource, rid=key, page=page)

            if 'per' in request.args:
                href = url_for('apd_view', resource=resource, rid=key, page=page, per=per)

            itemlist.append({
                'id' : key,
                'rel' : resource+'/'+str(key),
                'name' : name,
                'href' : href
                })

        return template('base_list.html', dict(
            items=itemlist, count=count, resource=resource, 
            href=url_for('apd_list', resource=resource, page=page, **all_args),
            page=page, prev=prev_page, next=next_page, total_pages=total_pages,
            per=per, start=(page-1)*per+1, end=min(count,page*per),
            filter_form=ff
            ))
    else:
        raise ResponseError() 


# - search
#   GET:
#       Display a search form.
#   POST:
#       Perform full-text searches based on keywords.
@app.route('/apd/search')
@app.route('/apd/search/<qq>')
@login_required
def apd_search(qq=None):
    query = qq or request.args.get('q')
    d = {}

    if query:
        qs = [s.lower() for s in query.strip().split()]
        results = {}

        for resource, model in resources.items():
            if not hasattr(model, '_searchable'):
                continue

            idx = Subscription.available_items(g.user, resource)

            items = model.select()

            for fname in model._searchable:
                field = model._meta.fields[fname]

                for s in qs:
                    items = items.orwhere(field.contains(s))

            if items.count() == 0:
                continue

            results[resource] = []

            for item in items:
                key = item.get_key()
                subbed = g.user.is_admin or \
                    Subscription.can_access(g.user, resource, idx)

                results[resource].append({
                    'id' : key,
                    'rel' : resource+'/'+str(key),
                    'name' : item.get_name(),
                    'href' : url_for('apd_view', resource=resource, rid=key),
                    'subscribed': subbed
                    })

        d['query'] = query
        d['results'] = results

    return template('search.html', d)
