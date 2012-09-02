$(document).ready(function() {

  function follow() {
    var btn = $(this);
    btn.button('loading')
    $.ajax({url: btn.attr('href'), type: "POST", success: function() {
//      btn.button('reset') // there is a bug which makes this reset prevent disabling
      //btn.removeClass('btn-primary ajax-btn');
      btn.siblings().show()
      btn.hide()
      btn.button('reset')
      //btn.off('click', follow)
      }})
  }

  $('.ajax-btn').on('click', follow);

  $('#addtogroup_modal').on('show', function (e) {
    $this = $(e.target)
    $this.find('.modal-body').html($this.data('modal').options.modaltext)
    console.log($this.data('modal').options.modaltext)
    return true
  })
  
  $('#addtogroup_modal .btn-primary').on('click', function (e) {
    $m = $('#addtogroup_modal').data('modal')
    $.post($m.options.action, 'players='+$m.options.player)
    //$('#addtogroup_modal').
    return false
  })
  
  $('#sendmessage_modal').on('show', function(e) {
    var m = $(e.target).data('modal')
    var blody = m.$element.find('.modal-blody')
    m.options.remote && blody.load(m.options.remote)
  })
  
  $('#sendmessage_modal').on('shown', function(e) {
    $m = $(e.target).find('.modal-body')
    //$m.prop('scrollTop', $m.prop('scrollHeight') - $m.height())
    $m.animate({scrollTop: $m.prop('scrollHeight') - $m.height()}, 500)    
  })
  
  function post_ajax(e) {
    // Need to attach this to modal main div, as the form is recreated every click
    // so we pick up the form from the event target, not "this"
    $this = $(this);
    $form = $(e.target);
    if($form.size() > 0) {
      $form = $($form[0]);
      console.log("Posting "+$form.serialize()+" to "+$form.attr('action'));
      $.post($form.attr('action'), $form.serialize(), function(data){
        $this.html(data);
      }).error(function() {
        $this.html('<div class="alert alert-error">Could not send message!</div>')
      });
      return false;
    } else {
      return true;
    }
  }

  //$('.modal-blody').on('submit', post_ajax(e));
  
});