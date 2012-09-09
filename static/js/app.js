$(document).ready(function() {

  function serializeObject(form) {
    var o = {};
    var a = form.serializeArray();
    $.each(a, function() {
      if (o[this.name] !== undefined) {
        if (!o[this.name].push) {
          o[this.name] = [o[this.name]];
        }
          o[this.name].push(this.value || '');
        } else {
          o[this.name] = this.value || '';
        }
    });
    return o;
  };
  
  jQuery.extend( {
    dictreplace: function(s, d) {
      if (s && d) {
        var p = s.split("__")
        for (i=1; i<p.length;i=i+2) {
          if (d[p[i]]) {
            p[i] = d[p[i]]
          }
        }
        return p.join('')
      }
      return s
    } 
  });  

  function changestate(e) {
    e.preventDefault()
    var btn = $(e.target);
    btn.button('loading')
    $.post(btn.attr('href'), '', function() {
        btn.button('reset')
        var s = parseInt(btn.data('state'))+1
        btn.trigger('nextstate', {state: s, resources: btn.data('resources')})
      }).error(function() {
        btn.html('Failed!').addClass('btn-danger')
        setTimeout(function() {btn.removeClass('btn-danger').button('reset')},2000)
      })
  }
  $('.comp').on('click', changestate); 

  function modalstate(e) {
    var $t = $(e.target);
    var $m = $t.data('modal')
    // Trigger state on modal, but take it from data(state) which has been set by
    // the calling button (as an option)
    $t.trigger('nextstate', {state: $m.options.state, resources: $m.options.resources })
    $t.on('submit', 'form', function() { // form here means a delegate selector, so we can catch
      var $f =$(this)
      $.post($f.attr('action'), $f.serialize(), function(data) {
        // success, find the calling button and send it to next state
        var $c = $($t.data('modal').options.caller)
        var s = parseInt($c.data('state'))+1
        $c.trigger('nextstate', {state: s, form: serializeObject($f), resources: $c.data('resources')})
        $t.html(data)
        if ($m.options.autoclose) {
          setTimeout(function() {$t.modal('hide')},2000)      
        }
      }).error(function() {
        $t.html('<div class="modal-header"><div class="alert alert-block alert-error">'+
                '<p>Request failed!</p></div></div>')
        setTimeout(function() {$t.modal('hide')},2000)
      })
      return false
    })}
  $('.modal').on('show', modalstate); 
  
  $('#sendmessage_modal').on('shown', function(e) {
    var $m = $(e.target).find('.modal-body')
    $m.animate({scrollTop: $m.prop('scrollHeight') - $m.height()}, 500)
  })

});