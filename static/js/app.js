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
  
  // Extends Typeahead with a different updater() function
  var extended_typeahead = {
    // remove the name and space from the username
    updater: function(item) { return item.replace(/ \(.*\)/,'') },
    matcher: function(item) { 
      var it=item.toLowerCase(), pre=it.split(" ")[0], qu = this.query.toLowerCase()
      return !~this.options.exclude.indexOf(pre) && ~it.indexOf(qu) // not in exclude and in query
    }
  }
  $.extend(true, $.fn.typeahead.Constructor.prototype, extended_typeahead)

  $('.typeahead-input input').keydown(function(e) {
    if (e.which == 188 && e.target.value.length > 0) {
      $(e.target).parent().before('<li class="typeahead-item">'+e.target.value+'<input type="hidden" name="players" value="'+e.target.value+'" /></li>')
      e.target.value=''
      return false
    } else if (e.which == 8 && e.target.value.length == 0) {
      $(e.target).parent().prev().remove()
      return false
    }
    return true;
  })
  .focus(function(e) {
    var $t = $(this)
    $t.parent().parent().addClass('typeahead-focus')
    var el, els = $($t.data('exclude-view')).find('.m_field[name="username"]'), s ="";
    for (var i = els.length - 1; i >= 0; i--) {
      el = $(els[i]); s += (el.data('value') ? el.data('value') : el.html()) + ",";
    }
    $t.data('typeahead').options.exclude = s.toLowerCase()
    return true;
  })
  .blur(function(e) {
    $(this).parent().parent().removeClass('typeahead-focus')
    return true;
  });
  
  $('.typeahead-item').on('click','.typeahead-item', function(e) {
    $(this).remove()
  });

  function post_action($t) {
    var vars, type = $t.data('action-type'), href=$t.attr('href'),
      action=href.replace(/.*\/([^/?]+)(\?.*)?\/?/, "$1"), // takes last word of url
      action_parent = $t.closest('.m_instance, .m_field, .m_view, .m_selector');
    if(type==='modal') {
      vars = $('#themodal').find('form').serialize()
    } else if (type==='inplace') {
      //vars = $t.parents('form').serialize()
    } else {
      vars = action_parent.find('input, textarea').serialize()
    }
    $t.button('reset') // reset button
    $.post(href + (href.indexOf('?') > 0 ? '&' : '?') + 'inline', vars, function(data) { // always add inline to the actual request
      var $d = $(data), $a = $d.filter('#alerts')
      var action_re = new RegExp(action+'(\\/?\\??[^/]*)?$') // replace the action part of the url, leaving args or trailing slash intact
      switch(action) {
        case 'add': if(action_parent.hasClass('m_selector')) {action_parent.replaceWith($d.filter('#changes').html()); break; }
        case 'new': action_parent.find('.m_instance').last().after($d.filter('#changes').html()); break;
        case 'edit': break;
        case 'remove': if(action_parent.hasClass('m_selector')) {action_parent.replaceWith($d.filter('#changes').html()); break; }
        case 'delete': action_parent.remove(); break;// remove the selected instance
        case 'follow': $t.html("Unfollow").toggleClass("btn-primary").attr('href',href.replace(action_re,'unfollow$1')); break;
        case 'unfollow': $t.html("Follow ...").toggleClass("btn-primary").attr('href',href.replace(action_re,'follow$1')); break;
        default:
      }

      if(type==='modal') { // show response in modal
        $('#themodal').html(data)
        setTimeout(function() {$('#themodal').modal('hide')},3000)
      } else if ($a.children().length > 0) {
        $t.popover({trigger: 'manual', html:true, content:$a.html()+'<div class="arrow"></div>',
          template:'<div class="popover popover-alert"><h3 class="popover-title"></h3><div class="popover-content"></div></div>'})
        $t.popover('show')
        $('body').one('click', function() {$t.popover('destroy')})
      }

    }).error(function(xhr, errorType, exception) {
      if(type==='modal') { $('#themodal').modal('hide') }
      var errorMessage = exception || xhr.statusText; //If exception null, then default to xhr.statusText  
      alert( "There was an error: " + errorMessage );
    });
  }

  function handle_action(e) {
    var $t = $(e.currentTarget); // current to make sure we capture the button with .m_action, not children of it
    if (!$t.hasClass('disabled')) { // if not disabled, means no action is current with this button
      $t.button('loading') // disables the button until we're done
      // preparations
      switch ($t.data('action-type')) {
        case 'modal':
          var href = $t.attr('href'), href = href + (href.indexOf('?') > 0 ? '&' : '?') + 'inline' //attach inline param
          $('#themodal').data('modal').options.caller = $t
          $('#themodal').load(href).modal('show'); break;
        case 'inplace': break;// replace instance with form
        default: // post directly
          post_action($t);
      }
    }
    e.preventDefault()
  }

  $('#themodal').modal({show:false})
  $('#themodal').on('submit', 'form', function(e) {
    if (e.target.action.match(/[?&]inline/)) {
      var $t = $(e.delegateTarget).data('modal').options.caller
      post_action($t) // trigger the action directly, as if it came from the button that brought up the modal
      e.preventDefault(); return false;  
    } // else, let the submit work as usual, redirecting the whole page
  }).on('hide', function(e) {
    var $t = $(e.delegateTarget).data('modal').options.caller
    $t.button('reset') // reset state
  }); 
  $('body').on('click', '.m_action', handle_action)

  $('.date-widget').datepicker({format: 'yyyy-mm-dd'});

  $('form select[data-role="chosen"]').chosen();
  $('form select[data-role="chosenblank"]').chosen({allow_single_deselect: true});

});