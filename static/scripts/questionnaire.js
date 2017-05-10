var DynamicIdentityFusionIndexInput = function ($el) {
  this.$el = $el;
  this.initializeDOM();
  this.update();
  this.render();
};

DynamicIdentityFusionIndexInput.prototype.initializeDOM = function () {
  // this.$el.attr('type', 'hidden');
  this.$content = $('<div class="DIFI"><div class="DIFI-group"><label></label></div><div class="DIFI-range"><div class="DIFI-me"><label>Me</label></div></div></div>');
  this.$me = this.$content.find('.DIFI-me');

  this.$group = this.$content.find('.DIFI-group');
  var group_label = this.$el.attr('data-group-label');
  this.$group.find('label').text(group_label);

  this.$content.insertBefore(this.$el);

  this.$me.draggable({
    axis: 'x',
    containment: 'parent',
    cursor: 'grabbing',
    start: function () {
      this.$me.addClass('dragging');
    }.bind(this),
    stop: function () {
      this.$me.removeClass('dragging');
      this.update();
    }.bind(this)
  });
};

DynamicIdentityFusionIndexInput.prototype.update = function () {
  // update value based on position
  var group_pos = this.$group.offset().left + this.$group.width() / 2;
  var me_pos = this.$me.offset().left + this.$me.width() / 2;
  var unit = this.$content.width() / 15;
  var x_small = (group_pos - me_pos) / unit;
  var value = 125 - 25 * x_small;
  this.$el.val(value);
};

DynamicIdentityFusionIndexInput.prototype.render = function () {
  var left = 20;
  var range = 60;
  var pos = left + (this.value / range);
  this.$me.css('left', pos + '%');
};


$(document).ready(function() {

  // Initialize DIFI widget
  var $DIFI = $('input.DIFI-input');
  if ($DIFI.length) {
  var input = new DynamicIdentityFusionIndexInput($DIFI);
  }

  // Submit the questionnaire.
  $("#submit-questionnaire").click(function() {
  console.log("Submitting questionnaire.");
  submitResponses();
  });
});
