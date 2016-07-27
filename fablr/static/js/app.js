svg4everybody(); // Do shim for IE support of external svg

/* ========================================================================
 * Helpers
 * ========================================================================
 * (c) Helmgast AB
 */
function flash_error(message, level, target) {
    message = message || 'Unknown error'
    target = $(target)
    if (!target.length)
        target = $('#alerts')

    if (message instanceof Object) {
        var new_message = ''
        Object.keys(message.errors).forEach(function (key, index) {
            new_message += key + ': ' + message.errors[key] + ', '
        });
        message = new_message
    } else if (message.indexOf('__debugger__') > 0) {
        // Response is a Flask Debugger response, overwrite whole page
        document.open();
        document.write(message);
        document.close();
        return false
    }

    var $error = $('<div class="alert alert-' + (level || 'warning') +
        ' alert-dismissable"> <button type="button" class="close"' +
        'data-dismiss="alert" aria-hidden="true">&times;</button>' +
        '<p>' + message + '</p>' +
        '</div>');
    target.append($error)
};

function decompose_url(url) {
    if (!url)
        return {}
    var a = document.createElement('a'), params = {}
    a.href = decodeURIComponent(url)
    // Search starts with ?, let's remove
    var query_parts = a.search.substring(1, a.search.length).split('&')
    for (var i = 0; i < query_parts.length; i++) {
        var nv = query_parts[i].split('=');
        if (!nv[0] || !nv[1]) continue;
        params[nv[0]] = nv[1] || true;
    }
    var i = a.pathname.lastIndexOf("/")
    var parts = {
        netloc: a.protocol + '//' + a.hostname + (a.port ? ":" + a.port : ""), path: a.pathname.substring(0, i + 1),
        file: a.pathname.substring(i + 1), hash: a.hash, params: params
    }
    // Remove parts that where not in original URL
    if (url.lastIndexOf('?', 0) === 0) {
        $.extend(parts, {netloc: '', path: '', file: ''})
    } else if (url.lastIndexOf('/', 0) === 0) {
        $.extend(parts, {netloc: ''})
    }
    return parts
}

// Adds, replaces or removes from current URL param string
function modify_url(url, new_params, new_url_parts) {
    var url = decompose_url(url)
    $.extend(url.params, new_params)
    $.extend(url, new_url_parts || {})
    return url.netloc + url.path + url.file + '?' + $.param(url.params) + url.hash;
}

/* ========================================================================
 * Autosave
 * ========================================================================
 * (c) Helmgast AB
 */
+function ($) {
    'use strict';

    $.fn.autosave = function (options) {
        return this.each(function () {
            var $this = $(this)

            var action = this.action || document.location.href
            var csrf = $this.find('#csrf_token').val()
            action = action + (/\?/.test(action) ? '&' : '?') + 'out=json'
            $this.change(function (e) {
                var $block = e.target.childNodes.length ? $(e.target) : $(e.target).parent()
                $block.addClass('loading')
                $.ajax({
                    url: action,
                    type: 'post',
                    data: $(e.target).serialize(),
                    headers: {'X-CSRFToken': csrf},
                    dataType: 'json',
                    success: function (data) {
                        $block.removeClass('loading')
                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        var error = JSON.parse(jqXHR.responseText)
                        flash_error(errorThrown)
                    }
                });
            })
        })
    }

    // Loaded in the bottom of app.js
    //$(window).on('load', function () {
    //    $('form[data-autosave]').each(function () {
    //        var $autosave_form = $(this)
    //        $autosave_form.autosave($autosave_form.data())
    //    })
    //})
}(jQuery);


/* ========================================================================
 * Editable list
 * ========================================================================
 * (c) Helmgast AB
 */
+function ($) {
    'use strict';

    $.fn.editablelist = function (options) {
        return this.each(function () {
            var $this = $(this)
            var remote = options['remote']
            var listname = options['editable']
            if (options['optionRemove'] != 'off')
                var $removeBtn = $('<button type="button" class="btn btn-default btn-xs btn-delete"><span class="glyphicon glyphicon-trash"></span></button>')
            if (options['optionAdd'] != 'off')
                var $addBtn = $('<button type="button" class="btn btn-primary btn-sm"><span class="glyphicon glyphicon-plus"></span> Add</button>')
            var $type = $this.prop('tagName');
            var selectors = {
                TABLE: {
                    eachItem: 'tr',
                    removeAt: ' td:last-child',
                    addAt: 'tbody'
                },
                UL: {
                    eachItem: 'li',
                    removeAt: '',
                    addAt: ''
                },
                DIV: {
                    eachItem: 'div.row',
                    removeAt: '',
                    addAt: ''
                }
            }
            selectors.OL = selectors.UL
            if (!selectors[$type])
                return // not correct type
            for (var opt in options) {
                if (selectors[$type][opt])
                    selectors[$type][opt] = options[opt]
            }
            if ($removeBtn) {
                $this.find(selectors[$type].eachItem + selectors[$type].removeAt).css('position', 'relative').append($removeBtn)
                $this.on('click', '.btn-delete', function () {
                    $(this).parents(selectors[$type].eachItem).first().remove()
                    $this.trigger('fablr.removed')
                })
            }
            if ($addBtn) {
                $addBtn.click(function () {
                    jQuery.get(remote, function (data) {
                        var newel = $(data)
                        // get # of rows, so we can correctly index the added inputs
                        var name = listname + '-' + $this.find(selectors[$type].eachItem).length + '-' + newel.find('input, select').first().attr('name')
                        newel.find('input, select, label').each(function () {
                            this.name = this.name && name
                            this.id = this.id && name
                            this.htmlFor = this.htmlFor && name
                        })
                        newel.append($removeBtn.clone())
                        selectors[$type].addAt ? $this.find(selectors[$type].addAt).append(newel) : $this.append(newel)
                        // TODO data activated js should be reloaded by throwing an event that the normal on load code can pick up
                    })
                })
                $this.after($addBtn)
            }
        })
    }

    // Loaded at bottom of app.js
    //$(window).on('load', function () {
    //    $('div, table, ul, ol').filter('[data-editable]').each(function () {
    //        var $editablelist = $(this)
    //        $editablelist.editablelist($editablelist.data())
    //    })
    //})
}(jQuery);

+function ($) {
    'use strict';
    var tempImage;
    var FileUpload = function (element, options) {
        var that = this;
        this.$el = $(element);
        this.$gallery = this.$el.closest('.gallery')
        this.$form = this.$el.find('form')
        this.options = options;

        this.$el.find('#file_data').on('change', that.fileSelected.bind(this));

        this.$el.find('label')
            .on('drop', this.fileSelected.bind(this))
            .on('dragover', function (e) {
                e.stopPropagation()
                e.preventDefault()
                e.originalEvent.dataTransfer.dropEffect = 'copy'
            })

        //$form.on('drag dragstart dragend dragover dragenter dragleave drop', function(e) {
        //e.preventDefault();
        //e.stopPropagation();
        //})
        //.on('dragover dragenter', function() {
        //$form.addClass('is-dragover');
        //})
        //.on('dragleave dragend drop', function() {
        //$form.removeClass('is-dragover');
        //})
        //.on('drop', function(e) {
        //droppedFiles = e.originalEvent.dataTransfer.files;
        //});

        tempImage = tempImage || new Image()
        this.$el.find('#source_file_url').on('input', function (e) {
            if (/^http(s)?:\/\/[^/]+\/.+/.test(e.target.value)) {
                tempImage.onload = that.fileSelected.bind(that) // bind to set this to that when called
                tempImage.src = e.target.value
                e.target.style.color = ''
            } else {
                tempImage.src = ''
                tempImage.onload = undefined
                e.target.style.color = 'red'
            }
        })

    }

    FileUpload.prototype.fileSelected = function (e) {
        var files = e.target.files || (e.originalEvent && e.originalEvent.dataTransfer.files) || [e.target]
        var formData, that = this; // save this reference as it will be changed inside nested functions

        e.stopPropagation();
        e.preventDefault();
        if (files) {
            $.each(files, function (i, file) {
                var $fig;
                formData = new FormData();
                formData.append('csrf_token', that.$form.find('input[name=csrf_token]').val())
                if (file.type && file.type.indexOf('image/') == 0) {
                    var reader = new FileReader()
                    $fig = $('<figure class="gallery-item loading loading-large"><img src=""></figure>')
                    var img = $fig.find('img')
                    reader.addEventListener("load", function () {
                        img.attr('src', reader.result);
                        $fig.data('aspect', img[0].width / img[0].height);
                        that.$el.after($fig)
                        that.$gallery.trigger('fablr.gallery-updated')
                    }, false);
                    // Read into a data URL for inline display
                    reader.readAsDataURL(file);
                    formData.append('file_data', file)
                } else if (file.type) {
                    var icon_url = that.options.static_url.replace('replace', 'img/icon/' + file.type.replace('/', '_') + '-icon.svg')
                    $fig = $('<figure class="gallery-item loading loading-large"><img src="' + icon_url + '"></figure>')
                    that.$el.after($fig)
                    that.$gallery.trigger('fablr.gallery-updated')
                    formData.append('file_data', file)
                } else if (file.src) {
                    formData.append('source_file_url', file.src)
                    $fig = $('<figure class="gallery-item loading loading-large"></figure>')
                    $fig.append(file)  // is a direct img node
                    $fig.data('aspect', file.width / file.height);
                    that.$el.after($fig)
                    that.$gallery.trigger('fablr.gallery-updated')
                }

                if ($fig) {
                    $.ajax({
                        url: that.$form.attr('action'),
                        type: 'POST',
                        data: formData,
                        dataType: 'json',
                        cache: false,
                        contentType: false,
                        processData: false,
                        complete: function (jqXHR, textStatus) {
                            if (textStatus != 'success' && textStatus != 'notmodified') {
                                flash_error(jqXHR.responseJSON || jqXHR.responseText, 'danger', $modal.find('#alerts'))
                                $fig.remove()
                                that.$gallery.trigger('fablr.gallery-updated')
                            } else {
                                // Trigger all plugins on added content
                                if ($fig.find('img').attr('src').match(/^data:/)) {
                                    console.log('TODO: replace this with original url')
                                }
                                $fig.removeClass('loading loading-large');
                            }
                        }
                    });
                } else {
                    flash_error('Unknown error', 'danger', $modal.find('#alerts'))
                }


            })
        }
        return false;
    }

    $.fn.fileupload = function (option) {
        return this.each(function () {
            var $this = $(this)
            var data = $this.data('fablr.fileselect')
            var options = $.extend(FileUpload.DEFAULTS, $this.data(), typeof option == 'object' && option)
            // If no data set, create a FileSelect object and attach to this element
            if (!data) $this.data('fablr.fileupload', (data = new FileUpload(this, options)))
            // if (typeof option == 'string') data[option](_relatedTarget)
            // else if (options.show) data.show(_relatedTarget)
        })
    }


}(jQuery);

+function ($) {
    'use strict';

    var FileSelect = function (element, options) {
        var that = this;
        this.options = options
        if (element) {
            this.$element = $(element)
            this.$element.addClass('hide')
            if (this.$element.attr('readonly') || this.$element.attr('disabled')) {
                this.$gallery = $('<figure class="gallery fileselect ' + (this.options.class || '') + '"></figure>');
            } else {
                this.$gallery =
                $('<a class="gallery fileselect ' + (this.options.class || '') + '" contenteditable="false" data-toggle="modal" data-target="#themodal"></a>');
            }
            this.selectFiles($.map(this.$element.find(':selected'), function (el) {
                return {id: el.value, slug: el.text}
            }));
            this.$element.after(this.$gallery)

            this.$gallery.on('hide.bs.modal.atbtn', function (e) {
                // Images have been selected
                that.selectFiles($.map($('#themodal').find("[data-selection]"), function (el) {
                    return {id: el.id, slug: $(el).find('.slug').text().trim()}
                }))
            })
        }
    }
    FileSelect.prototype.selectFiles = function (selected_files) {
        var that = this, select_params = [], gallery_html = '', options_html = '';
        (selected_files || []).forEach(function (file) {
            gallery_html += '<figure class="gallery-item"><img src="' + that.options.image_url.replace('replace', file.slug) + '"></figure>'
            options_html += '<option value="' + file.id + '" selected></option>';
            select_params.push(file.slug)
        });
        if (!options_html)
            options_html = '<option value="__None" selected>---</option>'
        this.$gallery.attr('href', modify_url(that.options.endpoint, {select: select_params.join()}))
        this.$gallery.html(gallery_html)
        this.$element.html(options_html)
        // TODO not working for some reason
        this.$gallery.trigger('fablr.dom-updated')

    }

    $.fn.fileselect = function (option) {
        return this.each(function () {
            var $this = $(this)

            var data = $this.data('fablr.fileselect')
            var options = $.extend(FileSelect.DEFAULTS, $this.data(), typeof option == 'object' && option)
            // If no data set, create a FileSelect object and attach to this element
            if (!data) $this.data('fablr.fileselect', (data = new FileSelect(this, options)))
        })
    }

    var defaultOptions = {};

    $.extend(true, $.trumbowyg, {
        langs: {
            // jshint camelcase:false
            en: {
                fileselect: 'Select File',
                file: 'File',
                uploadError: 'Error'
            }
        },
        // jshint camelcase:true

        plugins: {
            fileselect: {
                init: function (trumbowyg) {
                    trumbowyg.o.plugins.fileselect = $.extend(true, {}, defaultOptions, trumbowyg.o.plugins.fileselect || {fs_obj: new FileSelect('')});
                    trumbowyg.o.imgDblClickHandler = function (e) {
                        return false
                    }
                    trumbowyg.$c.on('click', '.gallery', function (e) {
                        var $figure = $(this).closest('.gallery');
                        select_image($figure)
                        return false
                    })
                    // Below is hack to avoid exception on focusnode being null
                    var r = document.createRange()
                    r.setStart(trumbowyg.$ta[0], 0)
                    r.setEnd(trumbowyg.$ta[0], 0)
                    document.getSelection().addRange(r)
                    console.log(document.getSelection().focusNode)

                    var select_image = function ($elem) {
                        trumbowyg.saveRange();
                        var select_params = [], insert_position = 'gallery-center';
                        if ($elem instanceof jQuery) {
                            $elem.find('img').each(function (i, el) {
                                select_params.push(decompose_url(el.src).file) // take filename part of URL
                            });
                            if ($elem.hasClass('gallery-wide')) {
                                insert_position = 'gallery-wide'
                            } else if ($elem.hasClass('gallery-side')) {
                                insert_position = 'gallery-side'
                            }
                        } else {
                            // Select closest element which is a direct child of the editor, will not select text nodes
                            $elem = $(trumbowyg.range && trumbowyg.range.startContainer).closest('.trumbowyg-editor > *')
                            if (!$elem.parents('#content-editor').length)
                                $elem = $('#content-editor *').first() // select first
                            $elem = $('<p>').insertBefore($elem)
                        }
                        // Calls a modal, we use an empty options object (with no remote to not start Bootstraps ajax load)
                        // Instead we create a fake target object with a href, that mimics what would normally be an <a>
                        $('#themodal').modal({}, {
                                href: modify_url(trumbowyg.o.image_select_url, {
                                    select: select_params.join(),
                                    position: insert_position
                                })
                            })
                            .one('hide.bs.modal', {t: trumbowyg, $elem: $elem}, function (e) {
                                var $newelem, selected = $('#themodal').find("[data-selection]").sort(function (a, b) {
                                    return $(a).data('selection') > $(b).data('selection')
                                });
                                var insert_choice = $('#insert-position .active input'), insert_position = 'gallery-center'
                                if (insert_choice.length) {
                                    insert_position = insert_choice[0].id
                                }
                                if (selected.length > 0) {
                                    $newelem = $('<ul contenteditable="false" class="gallery ' + insert_position + '"><li class="hide">' + insert_position + '</li></ul>')
                                    if (insert_position == 'gallery-wide')
                                        $newelem.attr('data-maxaspect', 100)
                                    selected.each(function (i, el) {
                                        var $el = $(el)
                                        $newelem.append('<li class="gallery-item" data-aspect="' + $el.data('aspect') + '"><img src="' + $el.find('img')[0].src + '"></li>')
                                    })
                                    $(e.data.$elem).replaceWith($newelem)
                                    $newelem.trigger('fablr.dom-updated')
                                    //e.data.t.restoreRange()
                                    //e.data.t.execCmd('insertImage', src, false, "donotuse");
                                } else {
                                    $(e.data.$elem).remove() // it's now empty
                                }
                                e.data.t.syncCode();
                                e.data.t.semanticCode(false, true);
                                e.data.t.updateButtonPaneStatus();
                                e.data.t.$c.trigger('tbwchange');
                            })
                    }

                    trumbowyg.addBtnDef('fileselect', {
                        fn: select_image,
                        ico: 'insert-image',
                        tag: 'gallery'
                    });


                },
                //tagHandler: function(element, t) {
                //    if (element.className.indexOf('gallery') > -1) {
                //        if (element.className.indexOf('wide') > -1) {
                //            return ['GALLERY', 'WIDE'];
                //        } else if (element.className.indexOf('portrait') > -1) {
                //            return ['GALLERY', 'PORTRAIT'];
                //        } else {
                //            return ['GALLERY', 'CENTER']; // fake tag, but will activate the gallery button
                //        }
                //    } else {
                //        return '';
                //    }
                //}
            }
        }
    });

}(jQuery);

/**
 * jQuery Unveil
 * A very lightweight jQuery plugin to lazy load images
 * http://luis-almeida.github.com/unveil
 *
 * Licensed under the MIT license.
 * Copyright 2013 Luís Almeida
 * https://github.com/luis-almeida
 */

;
(function ($) {

    $.fn.unveil = function (threshold, callback) {

        var $w = $(window),
            th = threshold || 0,
            retina = window.devicePixelRatio > 1,
            attrib = retina ? "data-src-retina" : "data-src",
            images = this,
            loaded;

        this.one("unveil", function () {
            var source = this.getAttribute(attrib);
            source = source || this.getAttribute("data-src");
            if (source) {
                this.setAttribute("src", source);
                if (typeof callback === "function") callback.call(this);
            }
        });

        function unveil() {
            var inview = images.filter(function () {
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

/* ========================================================================
 * Handle action buttons
 * ========================================================================
 * (c) Helmgast AB
 */
function post_action($t) {
    var vars, type = $t.data('action-type'), href = $t.attr('href'),
        action = href.replace(/.*\/([^/?]+)(\?.*)?\/?/, "$1"), // takes last word of url
        action_parent = $t.closest('.m_instance, .m_field, .m_view, .m_selector');
    if (type === 'modal') {
        vars = $('#themodal').find('form').serialize()
    } else if (type === 'inplace') {
        //vars = $t.parents('form').serialize()
    } else {
        vars = action_parent.find('input, textarea').serialize()
    }
    $t.button('reset') // reset button
    href = modify_url(href, {inline: true})
    $.post(href, vars, function (data) { // always add inline to the actual request
        var $d = $(data), $a = $d.filter('#alerts')
        var action_re = new RegExp(action + '(\\/?\\??[^/]*)?$') // replace the action part of the url, leaving args or trailing slash intact
        switch (action) {
            case 'add':
                if (action_parent.hasClass('m_selector')) {
                    action_parent.replaceWith($d.filter('#changes').html());
                    break;
                }
            case 'new':
                action_parent.find('.m_instance').last().after($d.filter('#changes').html());
                break;
            case 'edit':
                break;
            case 'remove':
                if (action_parent.hasClass('m_selector')) {
                    action_parent.replaceWith($d.filter('#changes').html());
                    break;
                }
            case 'delete':
                action_parent.remove();
                break;// remove the selected instance
            case 'follow':
                $t.html("Unfollow").toggleClass("btn-primary").attr('href', href.replace(action_re, 'unfollow$1'));
                break;
            case 'unfollow':
                $t.html("Follow ...").toggleClass("btn-primary").attr('href', href.replace(action_re, 'follow$1'));
                break;
            default:
        }

        if (type === 'modal') { // show response in modal
            $('#themodal').html(data)
            setTimeout(function () {
                $('#themodal').modal('hide')
            }, 3000)
        } else if ($a.children().length > 0) {
            $t.popover({trigger: 'manual', html: true, content: $a.html()})
            $t.popover('show')
            $('body').one('click', function () {
                $t.popover('destroy')
            })
        }

    }).error(function (xhr, errorType, exception) {
        if (type === 'modal') {
            $('#themodal').modal('hide')
        }
        var errorMessage = exception || xhr.statusText; //If exception null, then default to xhr.statusText
        alert("There was an error: " + errorMessage);
    });
}

function handle_action(e) {
    var $t = $(e.currentTarget); // current to make sure we capture the button with .m_action, not children of it
    if (!$t.hasClass('disabled')) { // if not disabled, means no action is current with this button
        $t.button('loading') // disables the button until we're done
        // preparations
        switch ($t.data('action-type')) {
            case 'modal':
                var href = $t.attr('href'), href = modify_url(href, {inline: true}) //attach inline param
//          $('#themodal').data('modal').options.caller = $t P: options.caller deprecated as of Bootstrap 3?
                $('#themodal').load(href).modal('show');
                break;
            case 'inplace':
                break;// replace instance with form
            default: // post directly
                post_action($t);
        }

    }
    e.preventDefault()
}

$('body').on('click', '.m_action', handle_action)

$('.selectize').on('selectize:unselect', function (e) {
    // TODO this is a hack to select the __None item, residing at index 0, to correctly empty the field
    if (e.currentTarget.selectedIndex == -1) {
        e.currentTarget.selectedIndex = 0;
    }
})

// Change to * if more than <a> needed
$('a[data-dismiss="back"]').click(function (e) {
    history.back();
    // Required, not sure why
    e.preventDefault();
});


//////////////// new modal code ///////////

// TODO replace with load_content when using Bootstrap 4, as it has deprecated own loading

$('#themodal').on('show.bs.modal', function (event) {
    if (event.relatedTarget && event.relatedTarget.href) {
        var $modal = $(this)
        // This is hack, normally remote would be populated but when launched manually from trumbowyg it isn't
        //$modal.data('bs.modal').options.remote = event.relatedTarget.href;
        load_content(event.relatedTarget.href, $modal.find('.modal-content'));
    }
    $(document).one('hide.bs.modal', '#themodal', function (e) {
        // We notify the originating button that modal was closed
        $(event.relatedTarget).trigger('hide.bs.modal.atbtn')
    });
});

// Catches clicks on the modal submit button and submits the form using AJAX
var $modal = $('#themodal')
$modal.on('click', 'button[type="submit"]', function (e) {
    var form = $modal.find('form')[0]
    if (form && form.action) {
        e.preventDefault()
        var jqxhr = $.post(form.action, $(form).serialize())
            .done(function (data, textStatus, jqXHR) {
                console.log(data)
                $modal.modal('hide')
            })
            .fail(function (jqXHR, textStatus, errorThrown) {
                flash_error(jqXHR.responseText, 'danger', $modal.find('#alerts'))
            })
    } else {
        $modal.modal('hide')
    }
});

function load_content(href, target, base_href, append) {
    var dest = $(target), parts = {}
    if (base_href) {
        parts = decompose_url(base_href)
        parts = {netloc: parts.netloc, path: parts.path, file: parts.file}
    }

    href = modify_url(href, {out: dest.hasClass('modal-content') ? 'modal' : 'fragment'}, parts)
    if (dest && href) {
        $.ajax({
                url: href,
                success: function (data, textStatus, jqXHR) {
                    if (textStatus != 'success' && textStatus != 'notmodified') {
                        flash_error(data, 'danger', $modal.find('#alerts'))
                    } else {
                        if (append) {
                            dest.append(data)
                        } else {
                            dest.html(data)
                        }
                        // Trigger all plugins on added content
                        dest.trigger('fablr.dom-updated')
                    }
                },
                dataType: 'html',
                xhrFields: {
                    withCredentials: true
                }
            }
        );
    }
}

$(document).on('click', '#content-editor a', function (e) {
    return false; // Ignore clicks on links in editor so we dont leave page
});

$(document).on('click', '#themodal a', function (e) {
    var $a = $(this), target = $a.attr('target'), $thm = $('#themodal')
    if (target !== '_blank') {
        load_content($a.attr('href'), target || $thm.find('.modal-content'), $thm.data('bs.modal').options.remote);
        return false
    } // else do nothing special
});

// Loads HTML fragment data into a container when a link is pressed
$('body').on('click', '.loadlink', function (e) {
    var $a = $(this), $parent = $a.parent()
    load_content($a.attr('href'), $parent, null, true);
    $a.remove()
    return false;
});

// Send feedback to Slack
$('#feedback-modal').on('submit', 'form', function (e) {
    var input = $(this).serializeArray()
    var type = input[0]['value'] || 'error'
    var desc = input[1]['value'] || 'none'
    var user = input[2]['value'] || 'Anonymous'
    var payload = {
        'attachments': [
            {
                "fallback": "Received " + type + ": " + desc,
                "pretext": "Received " + type + " for " + window.location,
                "text": desc,
                "author_name": user,
                "author_link": user.indexOf("@") > 0 ? "mailto:" + user : '',
                "color": type == 'error' ? "danger" : "warning"
            }
        ]
    }
    ga('send', 'event', type, '(selector)', desc);
    $.post(
        'https://hooks.slack.com/services/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',
        JSON.stringify(payload))
    e.preventDefault()
    $('#feedback-modal').modal('hide')
});

$(document).on('click', '.selectable', function (e) {
    var $target = $(e.currentTarget), sel = parseInt($target.attr('data-selection'));
    var $parent = $target.parent(), multi = $parent.data('selectmultiple');
    if (!multi) {
        // If single select, always remove all other selections
        $parent.find('[data-selection]').each(function (i, el) {
            $(el).removeAttr('data-selection')
        })
    }
    if (sel > 0) {
        $target.removeAttr('data-selection') // Remove old selection
        var $selected = $parent.find('[data-selection]');
        $selected.each(function (i, el) {
            var $el = $(el);
            var n = parseInt($el.attr('data-selection'));
            if (n > sel)
                $el.attr('data-selection', n - 1)

        });
    } else {
        var total = $parent.find('[data-selection]').length;
        $target.attr('data-selection', total + 1) // Add new selection with last index
        // No need to update previous selections
    }
});


$(document).on('ready fablr.dom-updated fablr.gallery-updated', function (e) {
    var list = $(e.target).find('.gallery');
    if (!list.length)
        list = [$(e.target)]; // the scope is gallery itself, so start from itself
    $.each(list, function (i, el) {
        var $el = $(el), max_aspect = $el.data('maxaspect') || 3.0, items = $el.find('.gallery-item'), sumaspect = 0.0,
            row = [], aspect;
        items.each(function (i, item) {
            item = $(item)
            row.push(item)
            aspect = parseFloat(item.data('aspect')) || 1.0;
            sumaspect += aspect;
            if (sumaspect > max_aspect || i == items.length - 1) {
                $.each(row, function (i, item) {
                    var w = (100 - row.length) * (parseFloat(item.data('aspect')) || 1.0) / sumaspect;
                    item.css('width', w + "%")
                });
                // set width for all in row
                row = [];
                sumaspect = 0.0
            }
        })
    })
});

/* ========================================================================
 * Loaders. Will run on document ready as well as own event fablr.dom-updated.
 * Trigger fablr.dom-updated after adding content to dom. It will only apply
 * the loaders on the e.target part of the tree (which by default is document)
 * ========================================================================
 */
$(document).on('ready fablr.dom-updated', function (e) {
    var scope = $(e.target)
    scope.find("a[data-toggle='tooltip']").tooltip()
    scope.find('.selectize').selectize()
    scope.find('.selectize-tags').selectize({
        delimiter: ',',
        persist: false,
        create: function (input) {
            return {
                value: input,
                text: input
            }
        }
    });
    scope.find('.selectize-file').selectize({
        render: {
            item: function (item, escape) {
                return '<img src="' + image_url.replace('replace', item.text) + '">';
            }
        }
    });

    flatpickr('.flatpickr')

    scope.find('form[data-autosave]').each(function () {
        var $autosave_form = $(this)
        $autosave_form.autosave($autosave_form.data())
    });
    scope.find('div, table, ul, ol').filter('[data-editable]').each(function () {
        var $editablelist = $(this)
        $editablelist.editablelist($editablelist.data())
    });
    scope.find('select.fileselect').fileselect({image_url: image_url});
    scope.find('.file-upload').fileupload({static_url: static_url});
    scope.find('.zoom-container .zoomable').on('click', function (e) {
        var $el = $(e.delegateTarget), $img = $el.find('img')
        var screenAspect = document.documentElement.clientWidth / document.documentElement.clientHeight;
        var img_aspect = $img.width() / $img.height()
        $el.toggleClass('zoomed')
        if (img_aspect > screenAspect) { // wider than screen
            $img.toggleClass('fill-width')
        } else {
            $img.toggleClass('fill-height')
        }
        return false;
    });

    scope.find('.calc[data-formula]').each(function (i, el) {
        var pattern = /#([a-zA-Z\d_.:]+)/gi
        var $el = $(el)
        var formula = $el.attr('data-formula')  // use attr as it will always come out as a string
        var ancestors = formula.match(pattern) || []

        ancestors.forEach(function (an) {
            $an = $(an)
            if (!$an.length)
                console.log(an + ' is not a valid id')
            if ($an.is('input, textarea')) {
                formula = formula.replace(an, "(parseInt(document.getElementById('" + an.substring(1) + "').value) || 0)")
            } else {
                formula = formula.replace(an, "(parseInt(document.getElementById('" + an.substring(1) + "').innerText) || 0)")
            }
            $an.on("click keyup", function (e) {
                $el.trigger('recalc')
            })
        })
        var func = "try { var val = " + formula
            + "; } catch(e) { var val = NaN; console.log(e) } this.innerText=val; this.click(); return false"//console.timeEnd("recalc")'//console.log(val); debugger;'
        var fn = Function(func)
        //console.log(func)
        $el.on('recalc', fn)
        fn.call(el) // Initialize the values
    })

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

// li class="total"
// "/text=|#order_lines-0-quantityval/val| * |.product_price/text|"


// +function ($) {
//   'use strict';

//     var self, CalcQuery = function (element, options) {
//       var q = $(element).data('calcquery'), vars = q.match(/\|.+?\|/g), varmap = {}
//       for (var i = 0, n=97; i<vars.length;i++) {
//         if (!varmap[vars[i]]) {
//           varmap[vars[i]] = String.fromCharCode(n++)
//           q = q.replace(vars[i], varmap[vars[i]])
//         }
//       }
//       for (var path in varmap) {
//         var p_parts = path.split('|/')[1].split('/')
//         var $path = $(p_parts[0])
//       }
//     }

//     $.fn.calcquery = function (option) {
//     return this.each(function () {
//       var $this   = $(this)
//       var data    = $this.data('fablr.calcquery')
//       var options = $.extend({}, CalcQuery.DEFAULTS, $this.data(), typeof option == 'object' && option)
//       // If no data set, create a ImageSelect object and attach to this element
//       if (!data) $this.data('fablr.calcquery', (data = new CalcQuery(this, options)))
//       // if (typeof option == 'string') data[option](_relatedTarget)
//       // else if (options.show) data.show(_relatedTarget)
//     })
//   }
//   $.fn.calcquery.Constructor = CalcQuery

//   $(window).on('load', function () {
//     $('[data-calcquery]').calcquery()
//   })

//  }(jQuery);

//+function ($) {
//    'use strict';
//
//    $(window).on('load', function () {
//        $('textarea, input').filter('[data-formula]').each(function () {
//            var $t = $(this)
//            var particles = $t.data('formula').split("->")
//            var source = particles[0]
//            var $target = $(particles[1])
//            $t.on("change keyup paste", function () {
//                $target.html(eval(source))
//            })
//        })
//    })
//}(jQuery);