/**
 * Created by martin on 2016-10-16.
 */

/* ========================================================================
 * Calculatable
 * ========================================================================
 * (c) Helmgast AB
 */
define(["jquery"], function ($) {
    'use strict';

    $.fn.calculatable = function (options) {
        return this.each(function () {
            var pattern = /#([a-zA-Z\d_.:]+)/gi
            var $el = $(this)
            var formula = $el.attr('data-formula')  // use attr as it will always come out as a string
            var ancestors = formula.match(pattern) || []

            ancestors.forEach(function (an) {
                var $an = $(an)
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
            fn.call($el[0]) // Initialize the values
        })
    }

});