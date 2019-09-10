import json
from peewee import ForeignKeyField, IntegerField, fn

def legend(fname):
    return ' '.join(map(lambda s: s.capitalize(), fname.split('_')))

def filter_form(model, as_json=False):
    '''
    Constructs a form for filtering from a model.
    Setting `json` to true will output compact JSON.
    '''

    form = {}

    if not hasattr(model, '_filter'):
        raise Exception('Model does not have _filter property.')

    for fname in model._filter:
        field = model._meta.fields[fname]
        leg = legend(fname)

        if isinstance(field, ForeignKeyField):
            rel_model = field.rel_model
            rows = rel_model.select(rel_model.orderfield(), rel_model.keyfield()).order_by(rel_model.orderfield())
            options = {r.get_name() : r.get_key() for r in rows}
            form[fname] = {
                    'type' : 'multiple',
                    'legend' : leg,
                    'exclusive' : False,
                    'options' : options
                    }

        elif isinstance(field, IntegerField):
            # Get min and max values
            min, max = model.select(
                    fn.Min(field), fn.Max(field)
                    ).scalar(as_tuple=True)

            if max-min > 5:
                form[fname] = {
                        'type' : 'int_range',
                        'legend' : leg,
                        'min' : min,
                        'max' : max,
                        'step' : 1,
                        }
            else:
                options = {str(i):i for i in range(min, max+1)}
                form[fname] = {
                        'type' : 'multiple',
                        'legend' : leg,
                        'exclusive' : False,
                        'options' : options
                        }

    return json.dumps(form, sort_keys=True, separators=(',',':')) if as_json else form
