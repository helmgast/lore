// IMPORTANT. This sets the STATIC_PATH to that of the server, in a global var (_page.html), so we don't need to hardcode it.
__webpack_public_path__ = STATIC_URL.replace('replace', '')+'dist/';

// Needed for all pages, and should be loaded first
var jQuery = require('jquery');
window.$ = window.jQuery = jQuery;  // Set global access to jquery object

// var svgs = require.context("../gfx/", false, /\.svg$/)

// svgs.keys().forEach(svgs); // Requires all files individually to call the sprite

// Load early in case of error below
let Sentry;
window.sentryReport = function(c) {}
if (typeof SENTRY_DSN !== 'undefined' && SENTRY_DSN) {
    Sentry = require('@sentry/browser');
    Sentry.init({dsn: SENTRY_DSN, 
        beforeSend(event) {
            // Check if it is an exception, if so, show the report dialog
            if (event.exception) {
              Sentry.showReportDialog();
            }
            return event;
          }});
    Sentry.configureScope((scope) => {
        scope.setUser(SENTRY_USER);
    });
    window.sentryReport = function(config) {
        if (!config.user && SENTRY_USER && 'email' in SENTRY_USER && 'username' in SENTRY_USER) {
            config.user = {email: SENTRY_USER.email, name: SENTRY_USER.username}
        }
        Sentry.showReportDialog(config);
    }
}

// Own plugins
var utils = require('utils');
window.utils = utils;
window.fetchJsonp = require('fetch-jsonp');
// require('editablelist.js'); // currently not used
// require('autosave.js')


// Styles. Always load for simplicity.
require('../css/custom_bootstrap.less')
require('selectize/dist/css/selectize.bootstrap3.css');
require('flatpickr/dist/flatpickr.min.css');
require('trumbowyg/dist/ui/trumbowyg.css');
require('../css/app.less');
require('../css/webfonts.css');
require('intro.js/introjs.css')


/* ========================================================================
 * Event management (Dependencies: jQuery and utils)
 * ========================================================================
 */

$('#themodal').on('show.bs.modal', function (event) {
    if (event.relatedTarget && event.relatedTarget.href) {
        var $modal = $(this)
        // This is hack, normally remote would be populated but when launched manually from trumbowyg it isn't
        //$modal.data('bs.modal').options.remote = event.relatedTarget.href;
        $modal.data('bs.modal').options['href'] = event.relatedTarget.href
        utils.load_content(event.relatedTarget.href, $modal.find('.modal-content'));
    }
    $(document).one('hide.bs.modal', '#themodal', function (e) {
        // We notify the originating button that modal was closed
        $(event.relatedTarget).trigger('hide.bs.modal.atbtn')
    });
});

// Catches clicks on the modal submit button and submits the form using AJAX
var $modal = $('#themodal')
$modal.on('click', 'button[type="submit"]', function (e) {
    var form = $modal.find('form:not(.notmodal)')[0]
    if (form && form.action) {
        e.preventDefault()
        var jqxhr = $.post(form.action, $(form).serialize())
            .done(function (data, textStatus, jqXHR) {
                console.log(data)
                $modal.modal('hide')
            })
            .fail(function (jqXHR, textStatus, errorThrown) {
                utils.flash_error(jqXHR.responseText, 'danger', $modal.find('#alerts'))
            })
    } else {
        $modal.modal('hide')
    }
});


$(document).on('click', '.buy-link', function (e) {
    var jqxhr = $.ajax({
        url: SHOP_URL,
        type: 'patch',
        data: {product: this.id},
        headers: {'X-CSRFToken': CSRF_TOKEN},
        dataType: 'json',
        success: function (data) {
            $c = $('#cart-counter')
            $c.find('.badge').html(data.instance.total_items)
            $c.addClass("bounce").one('animationend webkitAnimationEnd oAnimationEnd', function () {
                $c.removeClass("bounce");
            });
            $c.addClass("highlight")
        }
    })
        .fail(function (jqXHR, textStatus, errorThrown) {
            utils.flash_error(jqXHR.responseText)
        });
    e.preventDefault();
});

$(document).on('click', '.trumbowyg-editor a', function (e) {
    return false; // Ignore clicks on links in editor so we dont leave page
});

$(document).on('click', '#themodal a', function (e) {
    var $a = $(this), target = $a.attr('target'), $thm = $('#themodal')
    if (target !== '_blank') {
        utils.load_content($a.attr('href'), target || $thm.find('.modal-content'), $thm.data('bs.modal').options.remote);
        return false
    } // else do nothing special
});

// Loads HTML fragment data into a container when a link is pressed
$(document).on('click', '.loadlink', function (e) {
    var $a = $(this), $parent = $a.parent()
    utils.load_content($a.attr('href'), $parent, null, true);
    $a.remove()
    return false;
});

$('#feedback-ribbon').on('click', function(e) {
    if (Sentry) {
        Sentry.captureMessage("User report");
        sentryReport({
            title: "Give us feedback or report an error",
            subtitle: "",
            labelComments: "What's not working?"
        })

    }
    return false;
});

$(document).on('click', '.selectable', function (e) {
    var $target = $(this), sel = parseInt($target.attr('data-selection'));
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

$(document).on('click', '.zoomable', function (e) {
    var $el = $(this)//, $img = $el.find('img')
    // var screenAspect = document.documentElement.clientWidth / document.documentElement.clientHeight;
    // var img_aspect = $img.width() / $img.height()
    if ($el.hasClass('zoomed')) {
        $el.removeClass('zoomed')
    } else {
        $el.addClass('zoomed')
    }
    // if (img_aspect > screenAspect) { // wider than screen
    //     $img.toggleClass('fill-width')
    // } else {
    //     $img.toggleClass('fill-height')
    // }
    return false;
});

// Smooth scroll for anchor links
$(document).on('click', 'a[href*=\\#]', function (event) {
    if (this.hash) {
        event.preventDefault();
        $('html,body').animate({scrollTop: $(this.hash).offset().top}, 500);
    }

});

/* ========================================================================
 * All events that should run on DOM first ready and at update.
 * ========================================================================
 */
function init_dom(e) {
    // e will be the jquery object if called at DOMLoaded, otherwise the e.target is the node that triggered
    var scope = e === $ ? $(document) : $(e.target)

    // Bootstrap plugins
    // Loads themselves. Load at all pages!
    require('bootstrap/js/dropdown');
    require('bootstrap/js/modal');
    require('bootstrap/js/alert');
    require('bootstrap/js/collapse');
    require('bootstrap/js/button');
    require('bootstrap/js/transition');
    require('bootstrap/js/carousel');

    // Bootstrap tooltip
    require('bootstrap/js/tooltip');
    scope.find("a[data-toggle='tooltip']").tooltip(); // Need to activate manually

    if (typeof TOUR_OPTIONS !== "undefined" && TOUR_OPTIONS) {
        var params = utils.decompose_url(window.location.href).params
        var step = parseInt(params['step'] || 1) - 1
        var introJs = require('intro.js').introJs();
        introJs.setOptions(TOUR_OPTIONS[step])
        introJs.start().oncomplete(function (e) {
            if (TOUR_OPTIONS[step]['nextUrl']) {
                window.location = TOUR_OPTIONS[step]['nextUrl'];
            } else {
                var jqxhr = $.ajax({
                    url: FINISH_TOUR_URL,
                    xhrFields: {
                        withCredentials: true
                    },
                    type: 'patch',
                    data: {},
                    dataType: 'json',
                    success: function (data) {
                        console.log('Finished')
                    }
                })
                    .fail(function (jqXHR, textStatus, errorThrown) {
                        utils.flash_error(jqXHR.responseText)
                    });
            }
        })


    }
    // Selectize plugin for SELECTS in forms
    require('selectize');

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

    // Flatpickr for date-felds in forms
    var flatpickr = require('flatpickr');
    scope.find('.flatpickr-datetime').flatpickr({
        "enableTime": true,
        "mode": "single",
        "enableSeconds": true,
        "time_24hr": true,
        "allowInput": true
    })

    // Autosize plugin
    var autosize = require('autosize')
    autosize(scope.find('textarea')); // Activate on textareas

    // File upload plugin for file upload forms
    require('fileuploader.js')
    scope.find('.file-upload').fileupload({static_url: STATIC_URL});

    // File select plugin (activates the jquery part, the trumbowyg part loads with trumbowyg later)
    require('fileselect.js')
    scope.find('.fileselect').fileselect({image_url: IMAGE_URL, link_url: LINK_URL});

    // Calculatable plugin
    require('calculatable.js')
    scope.find('.calc[data-formula]').calculatable();

    var throttle = require('lodash/throttle')

    // Zoombrand plugin
    var zoombrand = scope.find('.animated-move');
    if (zoombrand.length) {
        // var frombox = $('#zoombrand-from').get(0).getBoundingClientRect()
        utils.match_pos(zoombrand, '#zoombrand-from', {opacity: '1', position: 'absolute'})
        // zoombrand.css({opacity: '1', top: frombox.top+"px", left: frombox.left+"px", width: frombox.width+"px", height: frombox.height+"px"})

        // var from = zoombrand.get(0), to = $(zoombrand.data('to')).get(0)
        // if (from && to) {
        //     var valueFeeder = function (i, matrix) {
        //         var f = from.getBoundingClientRect(), t = to.getBoundingClientRect(),
        //             p_start = [f.left, f.top + window.scrollY],
        //             v = utils.vector_sub(p_start, [t.left, t.top]),
        //             len = utils.vector_len(v),
        //             new_v = utils.vector_sub(p_start, utils.vector_scale(utils.vector_unit(v), i * len)),
        //             max_scale = Math.min(f.width / t.width, f.height / t.height),
        //             sc = max_scale - i * (max_scale - 1);
        //         return matrix.scale(sc, sc).translate(new_v[0] + t.width * (sc - 1) * 0.5, new_v[1] + t.height * (sc - 1) * 0.5, 0);
        //     }
        toggled = false;
        var scroll_f = function () {
            // console.log('scrolled')
            if ($(window).scrollTop() > 50) {
                if (!toggled) {
                    utils.match_pos(zoombrand, '.navbar-brand')
                    toggled = true;
                }
            } else {
                if (toggled) {
                    utils.match_pos(zoombrand, '#zoombrand-from', {}, add_scroll=true)
                    toggled = false;
                }
            }
        }
        $(window).on('scroll', throttle(scroll_f, 100));
    }


    scope.find('.content-editor').each(function (e) {
        // Loads these dependencies asynchronously if we find this scope on the current page
        require.ensure(['trumbowyg', 'fileselect.js', 'trumbowyg.fileselect.js', 'trumbowyg.markdown.js'], function (require) {
            // Trumbowyg plugin for textareas
            require('trumbowyg')
            require('trumbowyg.fileselect.js')  // File select trumbo plugin
            require('trumbowyg.markdown.js')  // Markdown coversion to underlying textarea

            // Set path to SVG, will be fetched by trumbowyg using XHR
            $.trumbowyg.svgPath = require('trumbowyg/dist/ui/icons.svg')
            var $textarea = $('.content-editor')

            $textarea.trumbowyg({
                btns: ['strong', 'em', '|', 'formatting', 'unorderedList', 'orderedList', 'link',
                    ['fileselect', 'wide', 'center', 'portrait'], 'viewHTML', 'fullscreen'],
                autogrow: true,
                removeformatPasted: true,
                image_select_url: IMAGE_SELECT_URL
            })
        });

    })


}

// function update_gallery(e) {
//     // No dependency
//     var list = $(e.target).find('.gallery').addBack('.gallery'); // addBack adds the $(e.target) if it also matches .gallery
//     $.each(list, function (i, el) {
//         var $el = $(el), max_aspect = $el.data('maxaspect') || 3.0, items = $el.find('.gallery-item'), sumaspect = 0.0,
//             row = [], aspect;
//         items.each(function (i, item) {
//             item = $(item)
//             row.push(item)
//             aspect = parseFloat(item.data('aspect')) || 1.0;
//             sumaspect += aspect;
//             if (sumaspect > max_aspect || i == items.length - 1) {
//                 $.each(row, function (i, item) {
//                     var w = (100 - row.length) * (parseFloat(item.data('aspect')) || 1.0) / sumaspect;
//                     item.css('width', w + "%")
//                 });
//                 // set width for all in row
//                 row = [];
//                 sumaspect = 0.0
//             }
//         })
//     })
// }

$(init_dom)
$(document).on('lore.dom-updated', init_dom);
