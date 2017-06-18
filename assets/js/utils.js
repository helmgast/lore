/**
 * Created by martin on 2016-10-09.
 */

/* ========================================================================
 * Helpers
 * ========================================================================
 * (c) Helmgast AB
 */
function flash_error(message, level, target) {
    message = message
    target = $(target)
    if (!target.length)
        target = $('#alerts')

    if (message instanceof Object && message.errors) {
        var new_message = ''
        Object.keys(message.errors).forEach(function (key, index) {
            new_message += key + ': ' + message.errors[key] + ', '
        });
        message = new_message
    } else if (message.length && message.indexOf('__debugger__') > 0) {
        // Response is a Flask Debugger response, overwrite whole page
        document.open();
        document.write(message);
        document.close();
        return false
    } else {
        message = 'Unknown error'
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
        params[nv[0]] = decodeURIComponent(nv[1].replace(/\+/g, '%20')) || true;
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

function serializeObject(form) {
    var o = {};
    var a = form.serializeArray();
    $.each(a, function () {
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

function dictreplace(s, d) {
    if (s && d) {
        var p = s.split("__")
        for (i = 1; i < p.length; i = i + 2) {
            if (d[p[i]]) {
                p[i] = d[p[i]]
            }
        }
        return p.join('')
    }
    return s
}

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

var snabbt = require('snabbt.js');

function print_rect(rect) {
    return "top: " + rect.top + " left: " + rect.left + " height: " + rect.height + " width:" + rect.width
}

function match_pos(el, match_el, extra_args, add_scroll) {
    var $el = $(match_el)
    if ($el && $el.get(0)) {
        var box = $el.get(0).getBoundingClientRect(), args = {
            top: (box.top + (add_scroll ? window.scrollY : 0)) + 'px',
            left: (box.left + (add_scroll ? window.scrollX : 0)) + "px",
            width: box.width + 'px',
            height: box.height + 'px'
        }
        $.extend(args, extra_args)
        // console.log("Brand " + el + " is at " + print_rect(el.get(0).getBoundingClientRect()) + ", and " + match_el + " is at " + print_rect(box) + ". Scroll at " + window.scrollY)
        el.css(args)
    }

}

function match_pos_snabb(el, match_el, extra_args) {
    var box_from = $(el).get(0).getBoundingClientRect(), box_to = $(match_el).get(0).getBoundingClientRect()
    snabbt(el, {
        position: [box_to.left - box_from.left, box_to.top - box_from.top, 0],
        scale: [box_to.width / box_from.width, box_to.height / box_from.height],
        transformOrigin: [0, 0, 0]
    })
    el.css(extra_args)
}


function vector_add(v1, v2) {
    return [v1[0] + v2[0], v1[1] + v2[1]]
}

function vector_sub(v1, v2) {
    return [v1[0] - v2[0], v1[1] - v2[1]]
}

function vector_unit(v) {
    var len = vector_len(v)
    return [v[0] / len, v[1] / len]
}

function vector_len(v) {
    return Math.sqrt(v[0] ^ 2 + v[1] ^ 2)
}

function vector_scale(v, d) {
    return [v[0] * d, v[1] * d]
}

module.exports.flash_error = flash_error;
module.exports.decompose_url = decompose_url;
module.exports.modify_url = modify_url;
module.exports.serializeObject = serializeObject;
module.exports.dictreplace = dictreplace;
module.exports.load_content = load_content;
module.exports.match_pos = match_pos;
module.exports.vector_add = vector_add;
module.exports.vector_sub = vector_sub;
module.exports.vector_unit = vector_unit;
module.exports.vector_len = vector_len;
module.exports.vector_scale = vector_scale;
