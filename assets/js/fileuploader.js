/**
 * Created by martin on 2016-10-16.
 */

/* ========================================================================
 * Fileuploader
 * ========================================================================
 * (c) Helmgast AB
 */
define(["jquery", "utils"], function ($, utils) {
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
                if (file.type && file.type.indexOf('image/') == 0) { // It's an image
                    var reader = new FileReader()
                    $fig = $('<figure class="gallery-item selectable loading loading-large"><img src=""></figure>')
                    var img = $fig.find('img')
                    reader.addEventListener("load", function () {
                        img.attr('src', reader.result);
                        that.$el.after($fig)
                    }, false);
                    // Read into a data URL for inline display
                    reader.readAsDataURL(file);
                    formData.append('file_data', file)
                } else if (file.type) { // It's an uploaded file
                    var icon_url = that.options.static_url.replace('replace', 'img/icon/' + file.type.replace('/', '_') + '-icon.svg')
                    $fig = $('<figure class="gallery-item selectable loading loading-large"><img src="' + icon_url + '"></figure>')
                    that.$el.after($fig)
                    formData.append('file_data', file)
                } else if (file.src) { // It's an Image object from an URL
                    formData.append('source_file_url', file.src)
                    $fig = $('<figure class="gallery-item selectable loading loading-large"></figure>')
                    $fig.append(file)  // is a direct img node
                    // set_aspect(file)
                    that.$el.after($fig)
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
                                utils.flash_error(jqXHR.responseJSON || jqXHR.responseText, 'danger', that.$el.closest('#alerts'))
                                $fig.remove()
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
                    utils.flash_error('Unknown error', 'danger', that.$el.closest('#alerts'))
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

});