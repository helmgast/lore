/**
 * Created by martin on 2016-10-16.
 */

/* ========================================================================
 * Autosave
 * ========================================================================
 * (c) Helmgast AB
 */
define(["jquery", "utils"], function ($, utils) {

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
                        utils.flash_error(errorThrown)
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
})