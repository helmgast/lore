/* ===========================================================
 * trumbowyg.fileselect.js v
 * Select files from Fablr backend for Trumbowyg
 * ===========================================================
 * Author : Helmgast AB

 */

(function ($) {
    'use strict';

    var defaultOptions = {
        //serverPath: './src/plugins/upload/trumbowyg.upload.php',
        //fileFieldName: 'fileToUpload',
        //data: [],
        //headers: {},
        //xhrFields: {},
        //urlPropertyName: 'file',
        //statusPropertyName: 'success',
        //success: undefined,
        //error: undefined
    };

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
                    trumbowyg.o.plugins.fileselect = $.extend(true, {}, defaultOptions, trumbowyg.o.plugins.fileselect || {});
                    var btnDef = {
                            fn: function () {
                                trumbowyg.saveRange();
                                var file,
                                    prefix = trumbowyg.o.prefix;
                                //load_modal()
                                $('#themodal').modal('show', {href:trumbowyg.o.image_select_url}).one('hide.bs.modal',
                                    function(e){

                                        console.log("closed")
                                })

                            },
                            ico: 'insert-image'
                        };

                    trumbowyg.addBtnDef('fileselect', btnDef);
                }
            }
        }
    });

})(jQuery);
