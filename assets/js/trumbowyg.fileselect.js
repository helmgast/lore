/**
 * Created by martin on 2016-10-16.
 */

/* ========================================================================
 * Trumbowyg plugin: FileSelect
 * ========================================================================
 * (c) Helmgast AB
 */
define(["jquery", "utils"], function ($, utils) {
    'use strict';

    var defaultOptions = {};

    $.extend(true, $.trumbowyg, {
        langs: {
            en: {
                fileselect: 'Select File',
                file: 'File',
                uploadError: 'Error'
            }
        },

        plugins: {
            fileselect: {
                init: function (trumbowyg) {

                    // trumbowyg.o.plugins.fileselect = $.extend(true, {}, defaultOptions, trumbowyg.o.plugins.fileselect || {fs_obj: new FileSelect('')});
                    trumbowyg.o.imgDblClickHandler = function (e) {
                        load_gallery($(e.target))
                        return false
                    }
                    // Also apply when not on an image
                    trumbowyg.$c.parent().on('dblclick', '.trumbowyg .gallery', trumbowyg.o.imgDblClickHandler)

                    // trumbowyg.$c.on('click', '.gallery', function (e) {
                    //     var $figure = $(this).closest('.gallery');
                    //     load_gallery($figure)
                    //     return false
                    // })
                    // Below is hack to avoid exception on focusnode being null
                    var r = document.createRange()
                    r.setStart(trumbowyg.$ta[0], 0)
                    r.setEnd(trumbowyg.$ta[0], 0)
                    document.getSelection().addRange(r)
                    // console.log(document.getSelection().focusNode)

                    var load_gallery = function ($elem) {
                        trumbowyg.saveRange();
                        var select_params = [], insert_position = 'gallery-center';
                        if ($elem instanceof jQuery) {
                            var $gallery = $elem.closest('.gallery')
                            // We can find a gallery as parent to this element, or it is a gallery
                            if ($gallery.length) {
                                $elem = $gallery // so that we replace the full gallery
                                $gallery.find('li').each(function (i, el) {
                                    if (el.children.length)
                                    // take filename part of URL either as image src or as a href
                                        select_params.push(utils.decompose_url(el.children[0].src || el.children[0].href).file);
                                });
                                if ($elem.hasClass('gallery-wide')) {
                                    insert_position = 'gallery-wide'
                                } else if ($elem.hasClass('gallery-card')) {
                                    insert_position = 'gallery-card'
                                }
                            // We clicked an image without a gallery parent, use it as input (and replace with gallery)
                            } else if ($elem.is("img")) {
                                select_params.push(utils.decompose_url($elem[0].src).file);
                            }
                        } else {
                            // We have come here clicking the button, no element is selected, find location through editor
                            // Select closest element which is a direct child of the editor, will not select text nodes
                            $elem = $(trumbowyg.range && trumbowyg.range.startContainer).closest('.trumbowyg-editor > *')
                            $elem = $('<p>').insertBefore($elem)
                        }
                        // Calls a modal, we use an empty options object (with no remote to not start Bootstraps ajax load)
                        // Instead we create a fake target object with a href, that mimics what would normally be an <a>
                        $('#themodal').modal({}, {
                            href: utils.modify_url(trumbowyg.o.image_select_url, {
                                select: select_params.join(),
                                position: insert_position
                            })
                        })
                            .one('hide.bs.modal', {t: trumbowyg, $elem: $elem}, function (e) {
                                // Re-create the gallery and insert
                                var $newelem, selected = $('#themodal').find("[data-selection]").sort(function (a, b) {
                                    return $(a).data('selection') > $(b).data('selection')
                                });
                                var insert_choice = $('#insert-position .active input'),
                                    insert_position = 'gallery-center'
                                if (insert_choice.length) {
                                    insert_position = insert_choice[0].id
                                }
                                if (selected.length > 0) {
                                    $newelem = $('<ul contenteditable="false" class="gallery ' + insert_position + '"><li class="hide">' + insert_position + '</li></ul>')
                                    selected.each(function (i, el) {
                                        var $el = $(el)
                                        if ($el.children().first().is('a')) {
                                            $newelem.append('<li class="gallery-item"><a href="' + $el.children().first().attr('href') + '">' + $el.children().first().text().trim() + '</a></li>')
                                        } else {
                                            $newelem.append('<li class="gallery-item"><img src="' + $el.find('img')[0].src + '"></li>')
                                        }
                                    })
                                    $(e.data.$elem).replaceWith($newelem)
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
                        fn: load_gallery,
                        ico: 'insert-image',
                        tag: 'gallery'
                    });

                },
            }
        }
    });

});