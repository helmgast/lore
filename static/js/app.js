
// Editable List plugin
+function ($) {
  'use strict';

  $.fn.editablelist = function (option) {
    return this.each(function () {
      var $this   = $(this)
      var remote  = $this.data('remote')
      var $button = $('<button type="button" class="btn btn-danger btn-xs deletebtn"><span class="glyphicon glyphicon-trash"></span></button>')
      var $add = $('<button type="button" class="btn btn-primary btn-sm"><span class="glyphicon glyphicon-plus"></span>Add</button>')
      var $type = $this.prop('tagName');
      
      if ($type == "TABLE") {
        $button = $button.wrap('<td></td>').parent()
        $this.find('tbody > tr').append($button)
        console.log("in here");
        $add.click(function() {
            jQuery.get(remote, function(data) {
              $this.find('tbody').append(data)
              $this.find('select[data-role="chosen"]').chosen(); // need to reactive chosen for any loaded html TODO, nicer way
            })
        })
        $button.click(function() {
            $button.parent("tr").remove();
        });
        $this.after($add)
      }
      else if ($type == "UL" || $type == "OL") {
        $this.children('li').addClass('editableListUl')
        $this.find('li').append($button);
        $this.find('li button').addClass('editableListRemove')
        
        $add.click(function() {
          jQuery.get(remote, function(data) {
            $this.append(data)
            $this.find('select[data-role="chosen"]').chosen(); // need to reactive chosen for any loaded html TODO, nicer way
          })
        })
      // Listening to class instead of $button to allow multiple removals.
      $('.editableListRemove').click(function(e) {
          $(this).parent('li').remove();
          e.preventDefault();
          return false;
      })
      
      // Likely to be a less demanding solution for this.
      $('.editableListUl').mouseover(function(e) {
          $(this).find('.editableListRemove').show();
      })
      $('.editableListUl').mouseout(function(e) {
          $(this).find('.editableListRemove').hide();
      })
        $this.after($add)
      }
      // var data    = $this.data('bs.carousel')
      // var options = $.extend({}, Carousel.DEFAULTS, $this.data(), typeof option == 'object' && option)
      // var action  = typeof option == 'string' ? option : options.slide

      // if (!data) $this.data('bs.carousel', (data = new Carousel(this, options)))
      // if (typeof option == 'number') data.to(option)
      // else if (action) data[action]()
      // else if (options.interval) data.pause().cycle()
    })
  }

  $(window).on('load', function () {
    $('[data-editable="list"]').each(function () {
      var $editablelist = $(this)
      $editablelist.editablelist($editablelist.data())
    })
  })
}(jQuery);

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

// Deprecated
/*
  
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

  */ 
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
        $t.popover({trigger: 'manual', html:true, content:$a.html()})
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
//          $('#themodal').data('modal').options.caller = $t P: options.caller deprecated as of Bootstrap 3?
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
  }).on('hide.bs.modal', function(e) { // P: options.caller deprecated, Updated to correct event
//    var $t = $(e.delegateTarget).data('modal').options.caller
//    $t.button('reset') // reset state
    $("button").button('reset'); // reset state of all buttons
    
  }); 
  $('body').on('click', '.m_action', handle_action)

  $('form select[data-role="chosen"]').chosen();
  $('form select[data-role="chosenblank"]').chosen();

  // Change to * if more than <a> needed
  $('a[data-dismiss="back"]').click(function(e) {
      history.back();
      // Required, not sure why
      e.preventDefault();
  });
});