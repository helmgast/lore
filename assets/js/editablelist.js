/**
 * Created by martin on 2016-10-16.
 */

/* ========================================================================
 * Editable list
 * ========================================================================
 * (c) Helmgast AB
 */
define(["jquery"], function ($) {
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
});