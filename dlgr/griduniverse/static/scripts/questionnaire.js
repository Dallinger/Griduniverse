/*global Dallinger, submitAssignment */

import { DIFIInput } from 'identityfusion';


$(document).ready(function() {

  // Initialize DIFI widget
  var $DIFI = $('input.DIFI-input');
  if ($DIFI.length) {
    var input = new DIFIInput(
      $DIFI.get(0),
      {
        groupLabel: $DIFI.attr('data-group-label'),
        groupImage: $DIFI.attr('data-group-image')
      }
    );
  }

  var spinner = Dallinger.BusyForm();

  // Submit the questionnaire.
  $("#submit-questionnaire").click(function() {
    console.log("Submitting questionnaire.");
    var $elements = [$("form :input"), $(this)];
    spinner.freeze($elements);
    Dallinger.submitQuestionnaire("questionnaire", submitAssignment);
  });

});
