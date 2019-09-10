var F = {

  _sep : '__',

  Input : function(owner, attributes, classes) {
    this.el = document.createElement('input');
    this.el.owner = owner;

    for (var key in attributes) {
      this.el.setAttribute(key, attributes[key]);
    }

    if (typeof classes !== 'undefined') {
      this.el.className = classes.join(' ');
    }

    this.set = function(key, val) {
      this.el.setAttribute(key, val);
    };

    this.unset = function(key) {
      this.el.removeAttribute(key);
    };

    this.get = function(key) { return this.el.getAttribute(key); };

    this.get_val = function() { return this.el.value; };
  },

  IntRangeFilter : function(name, att) {
    this.name = name;
    this.legend = att.legend;
    this.max = att.max;
    this.min = att.min;
    this.step = att.step;

    this.input_from = new F.Input(this, {
      name : this.name+'__from',
      max : this.max,
      min : this.min,
      step : this.step,
      type : 'number',
      value : this.min,
    });

    this.input_to = new F.Input(this, {
      name : this.name+'__to',
      max : this.max,
      min : this.min,
      step : this.step,
      type : 'number',
      value : this.max
    });

    //
    this.render = function(parent_element) {
      var fieldset = document.createElement('fieldset');
      var legend = document.createElement('legend');
      var div_from = document.createElement('div');
      var div_to = document.createElement('div');

      legend.textContent = this.legend;

      div_from.appendChild(this.input_from.el);
      div_from.className = 'filter-range-from';

      div_to.appendChild(this.input_to.el);
      div_to.className = 'filter-range-to';

      fieldset.appendChild(legend);
      fieldset.appendChild(div_from);
      fieldset.appendChild(div_to);
      parent_element.appendChild(fieldset);
    };

    this.check_int = function(val, def) {
      var v = parseInt(val);
      return (v !== NaN)? v : def;
    };

    this.update = function(filters) {
      var v_from = this.min;
      var v_to = this.max;

      if (filters.hasOwnProperty(this.name)) {
        var exprs = filters[this.name];

        for (var i=0; i<exprs.length; i++) {
          switch (exprs[i].op) {
            case 'gte':
              v_from = this.check_int(exprs[i].value, this.min);
              break;
            case 'lte':
              v_to = this.check_int(exprs[i].value, this.max);
              break;
            default:
          }
        }
      }

      this.input_from.set('value', v_from);
      this.input_to.set('value', v_to);
    };

    this.doinput = function() {
      var v_from = this.check_int(
          this.input_from.get_val(),
          this.min
          );

      var v_to = this.check_int(
          this.input_to.get_val(),
          this.max
          );

      if (v_from === this.min && v_to === this.max) {
        return false;
      } else {
        return [
          {op:'gte', value:v_from},
          {op:'lte', value:v_to}
        ];
      }
    };

    this.input_from.el.addEventListener('input', function(e) { 
      e.target.owner.doinput(); 
    });

    this.input_to.el.addEventListener('input', function(e) { 
      e.target.owner.doinput(); 
    });
  },

  MultipleFilter : function(name, att) {
    this.name = name;
    this.legend = att.legend;
    this.exclusive = att.exclusive;
    this.labels = [];
    this.inputs = [];
    this.nopts = 0;

    for (var key in att.options) {
      var val = att.options[key];
      var element_id = this.name + this.nopts;
      var lbl = document.createElement('label');
      lbl.setAttribute('for', element_id);
      lbl.textContent = key;
      lbl.className = 'filter-multiple-label';
      this.labels.push(lbl);

      this.inputs.push(new F.Input(this, {
        name : this.name,
        id : element_id,
        type : this.exclusive ? 'radio' : 'checkbox',
        value : val
      }, ['filter-multiple-option']));

      this.nopts++;
    }

    //
    this.render = function(parent_element) {
      var fieldset = document.createElement('fieldset');
      var legend = document.createElement('legend');
      legend.textContent = this.legend;
      fieldset.appendChild(legend);

      for (var i=0; i<this.nopts; i++) {
        fieldset.appendChild(this.inputs[i].el);
        fieldset.appendChild(this.labels[i]);
      }

      parent_element.appendChild(fieldset);
    };

    this.update = function(filters) {
      var values = this.inputs.map(function (cv) { return cv.get('value'); });
      var flt_values = [];
      
      if (filters.hasOwnProperty(this.name)) {
        if (filters[this.name][0].op === 'in') {
          var fvals = filters[this.name][0].value.split('|');
          fvals.forEach(function(cv) {flt_values.push(cv)});
        }
      }

      for (var i=0; i<values.length; i++) {
        if (flt_values.indexOf(values[i]) > -1) {
          this.inputs[i].el.checked = true;
        }
      }
    };

    this.doinput = function() {
      var values = [];

      for (var i=0; i<this.inputs.length; i++) {
        var input = this.inputs[i];
        console.log(this.labels[i].textContent, input.el.checked, input.get_val());
        if (input.el.checked) values.push(input.get_val());
      }

      return values.length>0 ? {op:'in', value:values.join('|')} : false;
    };

    this.inputs.forEach(function(cv) { 
      cv.el.addEventListener('click', function(e) {
        var vals = e.target.owner.doinput();
        console.log(this, vals);  
      });
    }, this);
  },

  qs_to_filters : function() {
    var ops = ['in', 'eq', 'new', 'gt', 'gte', 'lt', 'lte'];

    var query = window.location.search.substring(1);
    var vars = query.split('&');
    var extra_vars = [];
    var filters = {};

    for (var i=0; i<vars.length; i++) {
      var pair = vars[i].split('=');

      if (pair.length > 1) {
        if (pair[0].indexOf('flt') > -1) {
          var expr = pair[1].split(F._sep);

          if (expr.length === 3) {
            var field = expr[0];
            var op = expr[1];
            var value = expr[2];

            if (ops.indexOf(op) > -1) {
              if (filters.hasOwnProperty(field)) {
                filters[field].push({op:op, value:value});
              } else {
                filters[field] = [{op:op, value:value}];
              }
            }
          }
        } else {
          extra_vars.push(vars[i]);
        }
      }
    }

    return [filters, extra_vars];
  },

  filters_to_qs : function(filters, extra_vars) {
    var pairs = [];

    for (var field in filters) {
      var filter = filters[field];
      var p;

      if (Array.isArray(filter)) {
        filter.forEach(function (cv) {
          p = 'flt=' + [field, cv.op, cv.value].join(F._sep);
          pairs.push(p);
        });
      } else {
        p = 'flt=' + [field, filter.op, filter.value].join(F._sep);
        pairs.push(p);
      }
    }

    if (typeof extra_vars !== 'undefined') {
      if (extra_vars.length > 0) pairs = pairs.concat(extra_vars);
    }

    return pairs.join('&');
  },

  update_page : function(inputs) {
    var filters = {};

    inputs.forEach(function (cv) {
      var v = cv.doinput();
      if (v) filters[cv.name] = v;
    });

    var qs = F.filters_to_qs(filters);
    window.location.search = qs;
  },

  init : function(form) {
    var filter_div = document.getElementById('filter-container');
    var fe = F.qs_to_filters();
    var filters = fe[0];
    var inputs = [];

    var nflt = 0;

    for (var key in filters) {
      if (filters.hasOwnProperty(key)) nflt++;
    }

    for (var fname in form) {
      var field = form[fname];
      var inp;

      switch(field.type) {
        case 'int_range':
          inp = new F.IntRangeFilter(fname, field);
          break;

        case 'multiple':
          inp = new F.MultipleFilter(fname, field);
          break;
      }

      inp.render(filter_div);
      if (nflt > 0) inp.update(filters);
      inputs.push(inp);
    }

    var update_btn = document.createElement('button');
    update_btn.setAttribute('id', 'filter-update');
    update_btn.textContent = 'Apply Filters';
    update_btn.addEventListener('click', function (e) {
      F.update_page(inputs);
    });

    filter_div.appendChild(update_btn);

    if (nflt > 0) document.getElementById('filter-toggle').checked = true;
  },

};
