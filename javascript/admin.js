function forEachEl(ls, fn) {
  for (var i=0; i<ls.length; i++) fn(ls[i], i, ls);
}

function xhr(method, loc, auth, obj) {
  var req = new XMLHttpRequest();

  req.open(method, loc);
  req.setRequestHeader('Accept', 'application/json');

  if (typeof auth === 'string') {
    req.setRequestHeader('Authorization', auth);
  }

  if (typeof obj !== 'undefined') {
    req.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
    req.send(JSON.stringify(obj));
  } else {
    req.send();
  }

  return req;
}

function disableAllInputs(el) {
  var ls = el.getElementsByTagName('input');
  forEachEl(ls, function(v){v.disabled=true});
}

function enableAllInputs(el) {
  var ls = el.getElementsByTagName('input');
  forEachEl(ls, function(v){v.disabled=false});
}

var A = {

  getAuth: function() {
    var tok = document.cookie.replace(/cropdb_auth=([^;]*)$/, "$1");
    return 'Basic ' + window.btoa(tok+':');
  },

  updateInputs: function(subs) {
    for (var res in subs) {
      var all = subs[res].all;
      var idx = subs[res].idx;

      if (all) {
        var v = idx[0];
        var exp = (v.expires_in > 0)? '('+v.expires_in+'d)' : '(Expired)';
        document.getElementById(res+'-all').checked = true;
        document.getElementById('lbl-'+res+'-all').textContent += ' '+exp;
        disableAllInputs(document.getElementById(res+'-rest'));
      } else {
        idx.forEach(function(v) {
          var exp = (v.expires_in > 0)? '('+v.expires_in+'d)' : '(Expired)';
          document.getElementById(res+'-'+v.id).checked =  true;
          document.getElementById('lbl-'+res+'-'+v.id).textContent += ' '+exp;
        });
      }
    }
  },

  parseInputs: function(cbs, days) {
    var subs = {subscriptions:{}, extend_days:days};

    forEachEl(cbs, function(v) {
      if (v.checked && !v.disabled) {
        var res = v.getAttribute('data-resource');
        if (!subs.subscriptions.hasOwnProperty(res))
          subs.subscriptions[res] = [];
        subs.subscriptions[res].push(v.value);
      }
    });

    return subs;
  },

  init: function() {
    var sub_form = document.getElementById('subscriptions');
    var sub_btn = document.getElementById('update-subs');
    var userid = sub_form.getAttribute('data-user');
    var cbs = document.getElementsByName('sub-cb');
    var radios = document.getElementsByName('extend-months');
    var auth = A.getAuth();

    sub_btn.disabled = true;
    radios[0].checked = true;

    var req = xhr('GET', '/admin/subs/'+userid+'?t='+Date.now(), auth);

    req.addEventListener('load', function() {
      var req_obj = JSON.parse(req.responseText);

      if (req.status == 200) {
        // success
        A.updateInputs(req_obj.subscriptions);

        forEachEl(cbs, function(v) {
          v.addEventListener('click', function() {
            if (v.value == -1) {
              var res = v.getAttribute('data-resource');
              var rest = document.getElementById(res+'-rest');
              if (v.checked) disableAllInputs(rest);
              else enableAllInputs(rest);
            }

            sub_btn.textContent = 'Update';
            sub_btn.disabled = false;
          });
        });

        sub_btn.addEventListener('click', function(e) {
          e.preventDefault();

          if (!sub_btn.disabled) {
            sub_btn.textContent = 'Updating';

            var days = 30;
            forEachEl(radios, function(v) {if(v.checked) days=v.value*30});

            var subs = A.parseInputs(cbs, days);
            console.log(subs);

            var put_req = xhr('PUT', '/admin/subs/'+userid, auth, subs);
            put_req.addEventListener('load', function() {
              console.log(req.responseText);
              if (req.status == 200) {
                // success
                var ret = JSON.parse(put_req.responseText);
                sub_btn.textContent = 'Success';
                console.log(ret);
              } else {
                // failure
                sub_btn.textContent = 'Failed to update';
                A.updateInputs(req_obj.subscriptions);
              }
            });

            sub_btn.disabled = true;
          }

          sub_btn.blur();
        });
      } else {
        // failure
        sub_btn.textContent = 'Failed getting subscriptions';
      }
    });

    // User action buttons
    var action_btns = document.getElementsByName('user-action');

    forEachEl(action_btns, function(v) {
      var txt = v.textContent;
      var action = v.getAttribute('data-action');
      var obj = {action:action};

      v.addEventListener('click', function() {
        var put_req = xhr('PUT', '/admin/users/'+userid, auth, obj);
        v.textContent = 'Sending';
        put_req.addEventListener('load', function() {
          if (req.status == 200) {
            var ret = JSON.parse(put_req.responseText);
            console.log('WTF', ret);
            for (var k in ret.status) {
              document.getElementById('data-'+k).textContent = ret.status[k];
            }
            v.textContent = txt;
          } else {
            v.textContent = txt+' (Failed)';
          }
        });
      });
    });

  }
};
