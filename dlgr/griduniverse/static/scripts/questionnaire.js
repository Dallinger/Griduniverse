var DynamicIdentityFusionIndexInput = function ($el) {
  this.$el = $el;
  this.initializeDOM();
  this.update();
  this.render();
};

DynamicIdentityFusionIndexInput.prototype.initializeDOM = function () {
  var name = this.$el.attr('name');
  this.$el.attr('name', name + '_distance');
  this.$el.attr('type', 'hidden');
  this.$el_overlap = $('<input type="hidden" name="' + name + '_overlap" id="' + name + '_overlap" />').insertAfter(this.$el);
  this.$content = $(
'<div class="DIFI">' +
  '<div class="DIFI-controls"></div>' +
  '<div class="DIFI-group"><label></label></div>' +
  '<div class="DIFI-range">' +
    '<div class="DIFI-me"><label>Me</label></div>' +
  '</div>' +
'</div>');
  this.$me = this.$content.find('.DIFI-me');

  this.$group = this.$content.find('.DIFI-group');
  var group_label = this.$el.attr('data-group-label');
  this.$group.find('label').text(group_label);
  var group_image = this.$el.attr('data-group-image');
  if (group_image) {
    this.$group.css('backgroundImage', 'url(' + group_image + ')');
  }

  var $controls = this.$content.find('.DIFI-controls');
  $('<button type="button" class="button button-outline">&#9664;&#9664;</button>')
    .appendTo($controls)
    .click(this.nudge.bind(this, -0.5));
  $('<button type="button" class="button button-outline">&#9664;</button>')
    .appendTo($controls)
    .click(this.nudge.bind(this, -0.1));
  $('<button type="button" class="button button-outline">&#9654;</button>')
    .appendTo($controls)
    .click(this.nudge.bind(this, 0.1));
  $('<button type="button" class="button button-outline">&#9654;&#9654;</button>')
    .appendTo($controls)
    .click(this.nudge.bind(this, 0.5));

  this.$content.insertBefore(this.$el);

  this.$me.draggable({
    axis: 'x',
    containment: 'parent',
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
  // update value based on difference in position:
  // - left circle separated from right circle: -100 to 0
  // - left circle just touching right circle: 0
  // - left circle overlapping right circle: 0 to 100
  // - left circle contained within right circle: 100 to 125
  // - left circle at the center of right circle: 125
  var R = this.$group.outerWidth() / 2;
  var r = this.$me.outerWidth() / 2;
  var me_pos = this.outerLeft(this.$me);
  var group_pos = this.outerLeft(this.$group);
  var d = me_pos - group_pos;
  var value = 100 + 50 * d / r;
  // snap to center
  var $range = this.$me.parent();
  if (($range.offset().left + $range.outerWidth()) -
      (me_pos + this.$me.outerWidth()) < 2) {
    value = 125;
  }
  // clip value to desired range (-100 to 125)
  value = Math.max(Math.min(Math.round(value * 1000) / 1000, 125), -100);
  this.$el.val(value);

  // Compute overlap.
  d_center_to_center = (group_pos + R) - (me_pos + r);
  var overlap = this.calculateOverlap(d_center_to_center, r, R);
  this.$el_overlap.val(overlap);
};

DynamicIdentityFusionIndexInput.prototype.render = function () {
  var left = 10;
  var range = 60;
  var pos = left + (this.value / range);
  this.$me.css('left', pos + '%');
};

DynamicIdentityFusionIndexInput.prototype.nudge = function (delta) {
  var unit = this.$me.outerWidth() / 2;
  delta = delta * unit;
  var $container = this.$content.find('.DIFI-range');
  var minLeftDelta = $container.offset().left - this.outerLeft(this.$me);
  var maxRightDelta = (
    $container.offset().left + $container.width() -
    this.$me.outerWidth() - this.outerLeft(this.$me)
  );
  delta = Math.max(minLeftDelta, delta);
  delta = Math.min(maxRightDelta, delta);
  this.$me.css('left', this.$me.position().left + delta);
  this.update();
};

DynamicIdentityFusionIndexInput.prototype.outerLeft = function ($el) {
  return $el.offset().left - parseInt($el.css('border-left-width'), 10);
};

DynamicIdentityFusionIndexInput.prototype.calculateOverlap = function (d, r, R) {
  // d is the center-to-center spacing between the small and big circles.
  // r is the radius of the small circle.
  // R is the radius of the large circle.
  var x = (d*d + r*r - R*R) / (2*d*r);
  var y = (d*d + R*R - r*r) / (2*d*R);
  var z = (-d+r+R) * (d+r-R) * (d-r+R) * (d+r+R);
  overlap_area = r*r*Math.acos(x) + R*R*Math.acos(y) - Math.sqrt(z)/2;
  if (d > r + R) {
      return 0;
  } else if (d < R - r) {
      return 100;
  } else {
      return 100 * (overlap_area / (Math.PI*r*r));
  }
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
    Dallinger.submitQuestionnaire("questionnaire", submitAssignment);
  });
});
