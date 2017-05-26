/**
 * Created by martin on 2016-10-27.
 */

define(["jquery", "utils"], function ($, utils) {
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
                return {id: el.value, slug: el.text, type: that.options.class.indexOf('image') >= 0?'image':'document'}
            }));
            this.$element.after(this.$gallery) // Insert gallery after SELECT element

            this.$gallery.on('hide.bs.modal.atbtn', function (e) {
                // Images have been selected
                that.selectFiles($.map($('#themodal').find("[data-selection]"), function (el) {
                    var $el = $(el), slug = $el.find('.slug').text().trim();
                    if ($el.children().first().is('a')) {
                        return {id: el.id, slug: slug, type: 'document'}
                    } else {
                        return {id: el.id, slug: slug, type: 'image'}
                    }
                }))
            })
        }
    }
    FileSelect.prototype.selectFiles = function (selected_files) {
        var that = this, select_params = [], gallery_html = '', options_html = '';
        (selected_files || []).forEach(function (file) {
            if(file.id && file.id!='__None') {  // Ignore None if selected
                select_params.push(file.slug)
                options_html += '<option value="' + file.id + '" selected></option>';
                if (file.type =='image') {
                    gallery_html += '<figure class="gallery-item"><img src="' + that.options.image_url.replace('replace', file.slug) + '"></figure>'
                } else if (file.type =='document') {
                    gallery_html += '<figure class="gallery-item"><a href="' + that.options.link_url.replace('replace', file.slug) + '">'+file.slug+'</a></figure>'
                }
            }
        });
        if (!options_html)
            options_html = '<option value="__None" selected>---</option>'
        this.$gallery.attr('href', utils.modify_url(that.options.endpoint, {select: select_params.join()}))
        this.$gallery.html(gallery_html)
        this.$element.html(options_html)
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
});