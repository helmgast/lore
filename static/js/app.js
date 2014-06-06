function flash_error(message, level, target) {
  var $error = $('<div class="alert alert-'+(level || 'warning')+
            ' alert-dismissable"> <button type="button" class="close" \
            data-dismiss="alert" aria-hidden="true">&times;</button> \
            <p>'+message+'</p> \
            </div>');
  if ( target ) {
    $(target).append($error)
  } else {
    $('#alerts').append($error)
  }
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
        var $removeBtn = $('<button type="button" class="btn btn-default btn-xs btn-delete"><span class="glyphicon glyphicon-trash"></span></button>')
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
        $this.on('click','.btn-delete', function() {
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
        return $(this).find('img').data('aspect');
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
  // $(this).data('org-width', $(this)[0].width).data('org-height', $(this)[0].height);

}

/* Wait for images to be loaded */
$(window).on('load shown.bs.modal', function (e) {
  // Store original image dimensions
  $(e.target).find('.gallery img').each(saveImgSize);
  $(window).resize();
});

// $(document).on('', function (e) {
//     $(e.target).removeData('bs.modal'); // clears modals after they have been hidden
// });

$(document).ready(function() {
  $("a[data-toggle='tooltip']").tooltip()
});

// function serializeObject(form) {
//   var o = {};
//   var a = form.serializeArray();
//   $.each(a, function() {
//     if (o[this.name] !== undefined) {
//       if (!o[this.name].push) {
//         o[this.name] = [o[this.name]];
//       }
//         o[this.name].push(this.value || '');
//       } else {
//         o[this.name] = this.value || '';
//       }
//   });
//   return o;
// };

// jQuery.extend( {
//   dictreplace: function(s, d) {
//     if (s && d) {
//       var p = s.split("__")
//       for (i=1; i<p.length;i=i+2) {
//         if (d[p[i]]) {
//           p[i] = d[p[i]]
//         }
//       }
//       return p.join('')
//     }
//     return s
//   } 
// });  

/* ========================================================================
 * Image Selector
 * ========================================================================
 * Copyright Raconteur 2014

 * Activate on a button or input control, which will launch a modal to upload an 
 * image and place a preview in it. The modal will take care of all user 
 * interfacing and remove itself when done. The selected image can be represented 
 * as an image tag into a text field (e.g. an article text) or it can be added to 
 * a input control as the reference to the ImageAsset.

data-imageselector: activates the button or control as an image selector
data-target: the target is a selector. If the selector returns a compatible input
control, the value of it will be set to the image ID. Otherwise, an image element
will be appended to the target.

*/

+function ($) {
  'use strict';

  var tempImage;

  var self, ImageSelect = function (element, options) {
    self = this
    self.options   = options
    self.$element  = $(element)

    self.$imageEl = 
    $('<div class="image-selector" contenteditable="false"> \
        <div class="image-preview"> \
          <input type="text" class="image-preview-caption" placeholder="'+i18n['Caption']+'"> \
          <button type="button" class="btn btn-default btn-delete"><span class="glyphicon glyphicon-trash"></span></button> \
        </div> \
        <div class="image-upload form-group"> \
          <label for="imagefile" title="'+i18n['Drag or click to upload file']+'"> \
            <span class="glyphicon glyphicon-picture"></span> \
          </label> \
          <input type="file" class="hide" name="imagefile" id="imagefile" accept="image/*"> \
          <input type="text" class="form-control" name="source_image_url" \
          id="source_image_url" placeholder="http:// '+i18n['URL to image online']+'"> '+
          (options.image_list_url ? '<button type="button" data-toggle="modal" data-target="#large-modal" \
            data-remote="'+options.image_list_url+'" class="btn btn-info image-library-select">'+i18n['Select from library']+'</button>' : '') + 
        '</div></div>');
    
    self.$element.addClass('hide')
    self.$element.after(self.$imageEl)
    if (self.$element.is('select, input')) {
      self.setVal = function(src, slug) {
        self.$element.val(slug ? slug : '---')
      }
      var val = self.$element.val()
      if ( val && val!="__None")
        self.imageSelected('/asset/'+val, val)
    } else if (self.$element.is('a.lightbox')) {
      self.setVal = function(src, slug) {
        self.$element.attr('href', src)
        self.$element.find('img').attr('src', src)
      }
      if ( self.$element.attr('href'))
        self.imageSelected(self.$element.attr('href'))
    } else {
      console.log("ImageSelect doesn't work on this element")
      return
    }

    self.$imageEl.on('click', '.btn-delete', function(e){
      self.$imageEl.find('.image-preview img').remove()
      $('#large-modal .gallerylist input[type="radio"]:checked').prop('checked', false)
      self.$imageEl.find('.image-preview').removeClass('selected')
      self.$element.val('---') // blank choice in Select box...
    })

    $(document).on('hide.bs.modal', '#large-modal', function(e) {
      var $sel = $(this).find('.gallerylist input[type="radio"]:checked')
      if ($sel[0])
        self.imageSelected($sel.next('img')[0].src, $sel.val())
    })
    $('#imagefile').change(self.fileSelected)
    $('.image-upload label').on('drop', self.fileSelected).on('dragover', function(e) {
      e.stopPropagation()
      e.preventDefault()
      e.originalEvent.dataTransfer.dropEffect = 'copy'  
    })

    tempImage = tempImage || new Image()
    $('#source_image_url').on('input', function(e) {
      if ( /^http(s)?:\/\/[^/]+\/.+/.test(e.target.value)) {
        tempImage.onload = self.fileSelected
        tempImage.src = e.target.value
        e.target.style.color = ''
      } else {
        tempImage.src = ''
        tempImage.onload = undefined
        e.target.style.color = 'red'
      }
    })
  }

  ImageSelect.prototype.imageSelected = function(src, slug, no_set) {
    var div = self.$imageEl.find('.image-preview')
    div.children('img').remove()
    div.append('<img src="'+src+'">')
    self.$imageEl.find('.image-preview').addClass('selected')
    if(!no_set)
      self.setVal(src, slug)
  }

  ImageSelect.prototype.fileSelected = function (e) {
    var files = e.target.files || (e.originalEvent && e.originalEvent.dataTransfer.files)
      , formData = new FormData();
    if (files && files.length) {
      var file = files[0]
      var reader = new FileReader()
      reader.onload = (function(tfile) {
        return function(e) {
          self.imageSelected(e.target.result)
        };
      }(file));
      formData.append('imagefile', file)
      formData.append('title', file.name)
      reader.readAsDataURL(file);  
    } else if (e.target.src) {
      formData.append('source_image_url', e.target.src)
      formData.append('title', /[^/]+$/.exec(e.target.src)[0])
    } else {
      formData = null; return
    }

    formData.append('csrf_token', self.options.csrf_token)
    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", function() {
      var res = JSON.parse(this.responseText)
      if (this.status==200 && res.next) {
        self.imageSelected(res.next, res.item._id);
      } else {
        flash_error(res.message || 'unknown error', 'warning')
      }
    }, false);
    xhr.open('POST', self.options.image_upload_url)
    xhr.send(formData) // does not work in IE9 and below
    e.preventDefault()
  }

  $.fn.imageselect = function (option) {
    return this.each(function () {
      var $this   = $(this)
      var data    = $this.data('rac.imageselect')
      var options = $.extend(imageselect_options, ImageSelect.DEFAULTS, $this.data(), typeof option == 'object' && option)
      // If no data set, create a ImageSelect object and attach to this element
      if (!data) $this.data('rac.imageselect', (data = new ImageSelect(this, options)))
      // if (typeof option == 'string') data[option](_relatedTarget)
      // else if (options.show) data.show(_relatedTarget)
    })
  }
  $.fn.imageselect.Constructor = ImageSelect

  $(window).on('load', function () {
    $('[data-imageselect]').imageselect()
  })

 }(jQuery); 

$( '.lightbox' ).imageLightbox({
  onLoadStart:  function() { $('<div id="imagelightbox-loading"><div></div></div>').appendTo('body') },
  onLoadEnd:    function() { $('#imagelightbox-loading').remove() },
  onEnd:      function() { $('#imagelightbox-loading').remove() }
});

/**
 * jQuery Unveil
 * A very lightweight jQuery plugin to lazy load images
 * http://luis-almeida.github.com/unveil
 *
 * Licensed under the MIT license.
 * Copyright 2013 Luís Almeida
 * https://github.com/luis-almeida
 */

;(function($) {

  $.fn.unveil = function(threshold, callback) {

    var $w = $(window),
        th = threshold || 0,
        retina = window.devicePixelRatio > 1,
        attrib = retina? "data-src-retina" : "data-src",
        images = this,
        loaded;

    this.one("unveil", function() {
      var source = this.getAttribute(attrib);
      source = source || this.getAttribute("data-src");
      if (source) {
        this.setAttribute("src", source);
        if (typeof callback === "function") callback.call(this);
      }
    });

    function unveil() {
      var inview = images.filter(function() {
        var $e = $(this);
        if ($e.is(":hidden")) return;

        var wt = $w.scrollTop(),
            wb = wt + $w.height(),
            et = $e.offset().top,
            eb = et + $e.height();

        return eb >= wt - th && et <= wb + th;
      });

      loaded = inview.trigger("unveil");
      images = images.not(loaded);
    }

    $w.on("scroll.unveil resize.unveil lookup.unveil", unveil);

    unveil();

    return this;

  };

})(window.jQuery || window.Zepto);

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