
function flash_error(message, level) {
  var $error = $('<div class="alert alert-'+(level || 'warning')+
            ' alert-dismissable"> <button type="button" class="close" \
            data-dismiss="alert" aria-hidden="true">&times;</button> \
            <p>'+message+'</p> \
            </div>');
  $('#alerts').append($error)
};

/* ========================================================================
 * Editable list
 * ========================================================================
 * (c) Raconteur
 */
+function ($) {
  'use strict';

  $.fn.editablelist = function (option) {
    return this.each(function () {
      var $this   = $(this)
      var remote  = $this.data('remote')
      var listname = $this.data('editable')
      if ($this.data('option-remove')!= 'off' )
        var $removeBtn = $('<button type="button" class="btn btn-default btn-xs el-deletebtn"><span class="glyphicon glyphicon-trash"></span></button>')
      if ($this.data('option-add')!= 'off' )
        var $addBtn = $('<button type="button" class="btn btn-primary btn-sm"><span class="glyphicon glyphicon-plus"></span> Add</button>')
      var $type = $this.prop('tagName');
      var selectors = {
        TABLE : {
          item: 'tbody td:last-child',
          remove: 'tr',
          addTo : 'tbody'
        },
        UL : {
          item: 'li',
          remove: 'li',
          addTo : ''
        }
      }
      selectors.OL = selectors.UL
      if (!selectors[$type]) {
        return // not correct type
      }
      if ($removeBtn) {
        $this.find(selectors[$type].item).css('position', 'relative').append($removeBtn)
        $this.on('click','.el-deletebtn', function() {
          $(this).parents(selectors[$type].remove).first().remove()
        })
      }
      if ($addBtn) {
        $addBtn.click(function() {
          jQuery.get(remote, function(data) {
            var newel = $(data)
            // get # of rows, so we can correctly index the added inputs
            var name = listname +'-'+ $this.find(selectors[$type].item).length+'-'+newel.find('input, select').first().attr('name')
            newel.find('input, select, label').each(function() {
              this.name = this.name && name
              this.id = this.id && name
              this.htmlFor = this.htmlFor && name
            })
            newel.append($removeBtn.clone())
            selectors[$type].addTo ? $this.find(selectors[$type].addTo).append(newel) : $this.append(newel)
            // TODO data activated js should be reloaded by throwing an event that the normal on load code can pick up
            $this.find('select[data-role="chosen"]').chosen(); // need to reactivate chosen for any loaded html
          })
        })
        $this.after($addBtn)
      }
    })
  }

  $(window).on('load', function () {
    $('table, ul, ol').filter('[data-editable]').each(function () {
      var $editablelist = $(this)
      $editablelist.editablelist($editablelist.data())
    })
  })
}(jQuery);

/* ========================================================================
 * Fluid photoset
 * ========================================================================
 * From Terry Mun, http://codepen.io/terrymun/pen/GsJli
 */

(function($,sr){
// debouncing function from John Hann
// http://unscriptable.com/index.php/2009/03/20/debouncing-javascript-methods/
var debounce = function (func, threshold, execAsap) {
  var timeout;

  return function debounced () {
    var obj = this, args = arguments;
    function delayed () {
      if (!execAsap)
        func.apply(obj, args);
      timeout = null;
    };

    if (timeout)
      clearTimeout(timeout);
    else if (execAsap)
      func.apply(obj, args);

    timeout = setTimeout(delayed, threshold || 100);
  };
}
  // smartresize 
  jQuery.fn[sr] = function(fn){  return fn ? this.bind('resize', debounce(fn)) : this.trigger(sr); };

})(jQuery,'smartresize');

/* 
Wait for DOM to be ready
 */
$(function() {
  // Detect resize event
  $(window).smartresize(function () {
    // Set photoset image size
    $('.gallery-row').each(function () {
      var $pi    = $(this).find('.gallery'),
          cWidth = $(this).parent('.gallerylist').width();

      // Generate array containing all image aspect ratios
      var ratios = $pi.map(function () {
        return $(this).find('img').data('org-width') / $(this).find('img').data('org-height');
      }).get();

      // Get sum of widths
      var sumRatios = 0, sumMargins = 0,
          minRatio  = Math.min.apply(Math, ratios);
      for (var i = 0; i < $pi.length; i++) {
        sumRatios += ratios[i]/minRatio;
      };
      
      $pi.each(function (){
        sumMargins += parseInt($(this).css('margin-left')) + parseInt($(this).css('margin-right'));
      });

      // Calculate dimensions
      $pi.each(function (i) {
        var minWidth = (cWidth - sumMargins)/sumRatios;
        $(this).find('img')
          .height(Math.floor(minWidth/minRatio))
          .width(Math.floor(minWidth/minRatio) * ratios[i]);
      });
    });
  });
});

function saveImgSize() {
  $(this).data('org-width', $(this)[0].naturalWidth).data('org-height', $(this)[0].naturalHeight);
}

/* Wait for images to be loaded */
$(window).on('load', function (e) {
  // Store original image dimensions
  $(e.target).find('.gallery img').each(saveImgSize);
  $(window).resize();
});

$(document).on('hidden.bs.modal', function (e) {
    $(e.target).removeData('bs.modal'); // clears modals after they have been hidden
});

$(document).ready(function() {
$("a[data-toggle='tooltip']").tooltip()


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