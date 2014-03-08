/* http://github.com/mindmup/bootstrap-wysiwyg */
/*global jQuery, $, FileReader*/
/*jslint browser:true*/
(function ($) {
	'use strict';
	var readFileIntoDataUrl = function (fileInfo) {
		var loader = $.Deferred(),
			fReader = new FileReader();
		fReader.onload = function (e) {
			loader.resolve(e.target.result);
		};
		fReader.onerror = loader.reject;
		fReader.onprogress = loader.notify;
		fReader.readAsDataURL(fileInfo);
		return loader.promise();
	};

	var ENTER = 13, BACKSPACE = 8, TAB=9, DASH=189, INVISIBLE_SPACE = '\uFEFF';
	var IGNORE_KEYS = {16:'shift',17:'ctrl',18:'alt',224:'meta'};
	var lastType

	$.fn.doKey = function (e) {
		var select = $(this).getSelection();
		var newrow = select.startOffset == 0 && select.collapsed;
		var curEl = select.startContainer
		if (curEl.nodeName==='#text') {
			curEl = curEl.parentElement;
		}
		var tag = curEl.nodeName.toLowerCase();
		if (e.keyCode == ENTER) {
			e.preventDefault();
			if (!newrow) {
				if (tag !='li') {
					tag='p'; // only treat li special
				}
				$.fn.newElement(tag, curEl, true)
			} else {
				if (tag == 'p') {
					$.fn.newElement('h2', curEl)
				} else if (tag=='h2') {
					$.fn.newElement('h3', curEl)
				} else if (tag=='h3' || tag=='blockquote') {
					; // do nothing
				} else if (tag=='li') {
					var newCurEl =  curEl.parentElement
					$(curEl).remove() // remove the empty li, and append a p after the UL
					$.fn.newElement('p', newCurEl, true)			
				}
			}	
		} else if (e.keyCode == BACKSPACE) {
			if (select.startOffset <=1 && select.collapsed) { // will reach beginning of line after this
				$.fn.setHint($(curEl))
			}
			if (newrow) {
				e.preventDefault();
				var newtag = curEl.parentElement===this ? 'p' : 'none'
				if (tag=='h2' || tag=='h3' || tag=='blockquote') {
					$.fn.newElement(newtag, curEl);
				} else if (tag=='li' && curEl.parentElement.childElementCount <= 1) {
					newtag = curEl.parentElement.parentElement===this ? 'p' : 'none'
					$.fn.newElement(newtag, curEl.parentElement) // remove the whole ul in this case
				} else {
					$.fn.newElement(newtag, curEl)
				}
			} // let the backspace pass through
		} else if (e.keyCode == TAB) {
			e.preventDefault()
			if (newrow) {
				$.fn.newElement('blockquote', curEl)
			}
		} else if (e.keyCode == DASH) {
			if (newrow) {
				e.preventDefault()
				$.fn.newElement('ul', curEl)
			}
		} else if (!(e.keyCode in IGNORE_KEYS)) {
			$('#hinter').hide();
		}
	};

	$.fn.newElement = function (newtag, curEl, after) {
		var $h = $('#hinter');
		if (!newtag || newtag=='none') {
			$h.hide()
			if (curEl) {
				$.fn.selectElementText(curEl.previousElementSibling)
				$(curEl).remove();
			}
			return;
		} else {
			if (newtag=='ul') {
				var newEl = $('<'+newtag+'><li></li></'+newtag+'>');
			} else {
				var newEl = $('<'+newtag+'><br></'+newtag+'>');
			}
			if(after) {
				$(curEl).after(newEl);
			} else {
				$(curEl).replaceWith(newEl);
			}
			$.fn.selectElementText(newEl[0])			
		}
		$.fn.setHint(newEl);
	}

	$.fn.setHint = function (newEl) {
		var $h = $('#hinter');
		var newtag = newEl[0].nodeName.toLowerCase();
		if(!newEl) {
			$h.hide();
			return
		}

		if (newtag=='p') {
			newEl.clone().appendTo($h.empty()).text('Paragraph')
		} else if (newtag=='h2') {
			newEl.clone().appendTo($h.empty()).text('Section title');
		} else if (newtag=='h3') {
			newEl.clone().appendTo($h.empty()).text('Sub-section title');
		} else if (newtag=='blockquote') {
			newEl.clone().appendTo($h.empty()).text('Quote');
		} else if (newtag=='ul' || newtag=='li') {
			if(newtag=='li') {
				newEl = newEl.parent();
				newtag = 'ul';
			}
			var hintlist = newEl.clone()
			hintlist.children().empty().last().text('List')
			$h.empty().append(hintlist)
		}
		$h.css({left: newEl.position().left, top: newEl.position().top});
		$h.show();
	}

	$.fn.selectElementText = function(el, win){
        win = win || window;
        var doc = win.document, sel, range;
        if (!el) {
        	return;
        }
        if (win.getSelection && doc.createRange) {                    
            range = doc.createRange();
            range.selectNodeContents(el);
            range.collapse(false);
            sel = win.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        }
        else if (doc.body.createTextRange) {
            range = doc.body.createTextRange();
            range.moveToElementText(el);
            range.select();
        }
    };

	$.fn.cleanHtml = function () {
		var $t = $(this);
		var html = $t.html();
		/*
		Modifications:
		div -> 	p
		b ->	strong
		h1 -> 	h2
		i ->	em

		Kept tags:
		p ->	p
		blockquote -> blockquote
		h2 -> 	h2
		h3 ->	h3
		h4 ->	h4
		ul ->	ul
		ol ->	ol
		li ->	li
		strong -> strong
		em -> 	em
		*/
		html = html.replace(/(<\/?)div>/gi,'$1p>'); // all divs to p		
		html = html.replace(/(<\/?)h1>/gi,'$1h2>'); // all h1 to h2
		html = html.replace(/(<\/?)b>/gi,'$1strong>'); // all b to strong
		html = html.replace(/(<\/?)i>/gi,'$1em>'); // all i to em
		html = html.replace(/<(\w+) [^>]*>/g,'<$1>'); // remove all attr
		html = html.replace(/(&nbsp;)+/g,' '); // make spaces
		html = html.replace(/<(\/?(p|h2|h3|h4|blockquote|ul|ol|li|em|strong))>/gi,'%%%$1%%%'); // rename safe tags
		html = html.replace(/<\/?.+?>/g,''); // remove all remaining tags
		html = html.replace(/%%%(.+?)%%%/gi,'<$1>');
		// html = html.replace(/>(.+?)%%%/gi,'<$1>'); // TODO needed?
		html = html.replace(/<p>\s+<\/p>/gi,''); // remove empty p tags		
		$t.html(html);
		// $t.contents().filter(function() { return this.nodeType===3;}).wrap('<p />'); // wraps plain text nodes in p
		$t.contents(':empty').remove(); // removes empty nodes
		if (!$t.html() || $t.children().length == 0) { // if no nodes, put in empty placeholder
			$t.html('<p><br></p>');
		}
		return $t.html();
	};
	$.fn.tomarkdown = function () {
		var $t = $(this);
		$t.cleanHtml()
		// $t.detach()
		$t.find('p').each(function () {
			this.innerHTML = this.innerHTML+'\n\n'
		})	
		$t.find('em').each(function () {
			this.innerHTML = '_'+this.innerHTML+'_'
		})
		$t.find('strong').each(function () {
			this.innerHTML = '**'+this.innerHTML+'**'
		})
		$t.find('h2,h3,h4').each(function () {
			var hlevel = parseInt(this.nodeName.charAt(this.nodeName.length - 1))
			this.innerHTML = Array(hlevel+1).join('#') + ' '+ this.innerHTML + '\n\n' // repeats # char right times
		})
		$t.find('ul').each(function () {
			$(this).children('li').each(function(){
				this.innerHTML = '- '+this.innerHTML + '\n'
			})
			this.innerHTML = this.innerHTML+'\n'
		})
		$t.find('ol').each(function () {
			$(this).children('li').each(function (index) {
				this.innerHTML = (index+1)+'. '+this.innerHTML + '\n'// index is the counter for li items in each ol
			})
			this.innerHTML = this.innerHTML+'\n'
		})
		return $t.html().replace(/<\/?.+?>/g,'')
	}
	$.fn.clickHandler = function(e) {
		var selection = window.getSelection();
		var $target = $(e.target)
		var tparents = $target.parents('#editor-toolbar, #editor')

		if (tparents.length && tparents.get(0).id === 'editor-toolbar' ) {
			return // we simply just want this click to get through as is, to press the button
		}

		if ( selection.isCollapsed === true && lastType === false) {
			// no selection and we haven't started a selection
			$(this).removeToolbar()
		}
		if ( selection.isCollapsed === false) {
			// there is a selection
			if(tparents.length && tparents.get(0).id === 'editor') {
				$(this).moveToolbar(tparents.get(0))				
			}
		}
		lastType = selection.isCollapsed
	}

	$.fn.moveToolbar = function(editor) {
		var selection = window.getSelection();
		var $e = $('#editor-toolbar')
		var range = selection.getRangeAt(0);
		var boundary = range.getBoundingClientRect(); // position in viewport
		var offset = editor.getBoundingClientRect() // editor's position in viewport
		$e.css({top:(boundary.top-offset.top-55 + "px"),left:(boundary.left-offset.left + "px")}) // sets absolute position (from parent element)
		$e.addClass('in')	
	}
	$.fn.removeToolbar = function(e) {
		var $e = $('#editor-toolbar')
		$e.removeClass('in')
		$e.offset({top:-999,left:-999})
	}
	$.fn.wysiwyg = function (userOptions) {
		var editor = this,
			customCommandState = {},
			selectedRange,
			options,
			toolbarBtnSelector,
			updateToolbar = function () {
				if (options.activeToolbarClass) {
					$(options.toolbarSelector).find(toolbarBtnSelector).each(function () {
						var command = $(this).data(options.commandRole);
						if (queryCommandState(command)) {
							$(this).addClass(options.activeToolbarClass);
						} else {
							$(this).removeClass(options.activeToolbarClass);
						}
					});
				}
			},
			queryCommandState = function (cmd) {
				return (cmd in customCommandState) 
					? customCommandState[cmd] : document.queryCommandState(cmd)
			},
			execCommand = function (commandWithArgs, valueArg) {
				var commandArr = commandWithArgs.split(' '),
					command = commandArr.shift(),
					args = commandArr.join(' ') + (valueArg || '');
				if (command in options.customCommands) {
					customCommandState[command] = !customCommandState[command] // toggle
					options.customCommands[command](customCommandState[command])
				} else {
					document.execCommand(command, 0, args);
				}
				updateToolbar();					
			},
			bindHotkeys = function (hotKeys) {
				$.each(hotKeys, function (hotkey, command) {
					editor.keydown(hotkey, function (e) {
						if (editor.attr('contenteditable') && editor.is(':visible')) {
							e.preventDefault();
							e.stopPropagation();
							execCommand(command);
						}
					}).keyup(hotkey, function (e) {
						if (editor.attr('contenteditable') && editor.is(':visible')) {
							e.preventDefault();
							e.stopPropagation();
						}
					});
				});
			},
			getCurrentRange = function () {
				var sel = window.getSelection();
				if (sel.getRangeAt && sel.rangeCount) {
					return sel.getRangeAt(0);
				}
			},
			saveSelection = function () {
				selectedRange = getCurrentRange();
			},
			restoreSelection = function () {
				var selection = window.getSelection();
				if (selectedRange) {
					try {
						selection.removeAllRanges();
					} catch (ex) {
						document.body.createTextRange().select();
						document.selection.empty();
					}

					selection.addRange(selectedRange);
				}
			},
			insertFiles = function (files) {
				editor.focus();
				$.each(files, function (idx, fileInfo) {
					if (/^image\//.test(fileInfo.type)) {
						$.when(readFileIntoDataUrl(fileInfo)).done(function (dataUrl) {
							execCommand('insertimage', dataUrl);
						}).fail(function (e) {
							options.fileUploadError("file-reader", e);
						});
					} else {
						options.fileUploadError("unsupported-file-type", fileInfo.type);
					}
				});
			},
			markSelection = function (input, color) {
				restoreSelection();
				if (document.queryCommandSupported('hiliteColor')) {
					document.execCommand('hiliteColor', 0, color || 'transparent');
				}
				saveSelection();
				input.data(options.selectionMarker, color);
			},
			bindToolbar = function (toolbar, options) {
				toolbar.find(toolbarBtnSelector).click(function () {
					restoreSelection();
					editor.focus();
					execCommand($(this).data(options.commandRole));
					saveSelection();
				});
				toolbar.find('[data-toggle=dropdown]').click(restoreSelection);

				toolbar.find('input[type=text][data-' + options.commandRole + ']').on('webkitspeechchange change', function () {
					var newValue = this.value; /* ugly but prevents fake double-calls due to selection restoration */
					this.value = '';
					restoreSelection();
					if (newValue) {
						editor.focus();
						execCommand($(this).data(options.commandRole), newValue);
					}
					saveSelection();
				}).on('focus', function () {
					var input = $(this);
					if (!input.data(options.selectionMarker)) {
						markSelection(input, options.selectionColor);
						input.focus();
					}
				}).on('blur', function () {
					var input = $(this);
					if (input.data(options.selectionMarker)) {
						markSelection(input, false);
					}
				});
				toolbar.find('input[type=file][data-' + options.commandRole + ']').change(function () {
					restoreSelection();
					if (this.type === 'file' && this.files && this.files.length > 0) {
						insertFiles(this.files);
					}
					saveSelection();
					this.value = '';
				});
			},
			initFileDrops = function () {
				editor.on('dragenter dragover', false)
					.on('drop', function (e) {
						var dataTransfer = e.originalEvent.dataTransfer;
						e.stopPropagation();
						e.preventDefault();
						if (dataTransfer && dataTransfer.files && dataTransfer.files.length > 0) {
							insertFiles(dataTransfer.files);
						}
					});
			};
		options = $.extend({}, $.fn.wysiwyg.defaults, userOptions);
		$.fn.getSelection = getCurrentRange;
		toolbarBtnSelector = 'a[data-' + options.commandRole + '],button[data-' + options.commandRole + '],input[type=button][data-' + options.commandRole + ']';
		bindHotkeys(options.hotKeys);
		if (options.dragAndDropImages) {
			initFileDrops();
		}
		bindToolbar($(options.toolbarSelector), options);
		editor.attr('contenteditable', true)
			.on('mouseup keyup mouseout', function () {
				saveSelection();
				updateToolbar();
			});
		$(window).bind('touchend', function (e) {
			var isInside = (editor.is(e.target) || editor.has(e.target).length > 0),
				currentRange = getCurrentRange(),
				clear = currentRange && (currentRange.startContainer === currentRange.endContainer && currentRange.startOffset === currentRange.endOffset);
			if (!clear || isInside) {
				saveSelection();
				updateToolbar();
			}
		});
		return this;
	};
	$.fn.wysiwyg.defaults = {
		hotKeys: {
			'ctrl+b meta+b': 'bold',
			'ctrl+i meta+i': 'italic',
			'ctrl+u meta+u': 'underline',
			'ctrl+z meta+z': 'undo',
			'ctrl+y meta+y meta+shift+z': 'redo',
			'ctrl+l meta+l': 'justifyleft',
			'ctrl+r meta+r': 'justifyright',
			'ctrl+e meta+e': 'justifycenter',
			'ctrl+j meta+j': 'justifyfull',
			'shift+tab': 'outdent',
			// 'tab': 'indent'
		},
		customCommands: {},
		toolbarSelector: '[data-role=editor-toolbar]',
		commandRole: 'edit',
		activeToolbarClass: 'btn-info',
		selectionMarker: 'edit-focus-marker',
		selectionColor: 'darkgrey',
		dragAndDropImages: true,
		fileUploadError: function (reason, detail) { console.log("File upload error", reason, detail); }
	}
	;

	$(window).on('load', function () {
		$('[data-editable="textarea"]').each(function () {
			var $ta = $(this).toggleClass('hide')
			var $ed = $ta.data('target') && $($ta.data('target'))
			var customCommands = { 'customCommands': {
				'markdown': function(active) {
					// alert(active); // WARNING, CURRENTLY NOT WORKING
					if (active) {
						$ta.removeClass('hide')
						$ed.addClass('hide')
						$ta.val($ed.tomarkdown())
					} else {
						$ed.removeClass('hide')
						$ta.addClass('hide')
					}
				}
			}}
			$ed.toggleClass('hide').wysiwyg(customCommands)
			$ed.on('keydown', $ed.doKey)
			$ed.on('paste', function(e) {
          		$this = $(this)
          		setTimeout(function() {
            		$this.cleanHtml();
          		}, 10);
        	});
        	$(document).on('mousedown',$ed.clickHandler)
        	$(document).on('mouseup', function( event ) {
				setTimeout( function() {
					$ed.clickHandler( event );
				}, 1);
			})
			$('#hinter').tooltip({trigger:'manual',title:'Hej'})

        	$ta.parents('form').on('submit', function(e) {
        		if (!$ed.wysiwyg.options.customCommands['markdown'].active) {
          			$ed.cleanHtml()
          			$ta.val($ed.tomarkdown());
          		}
        	});
		})
	})
}(window.jQuery));