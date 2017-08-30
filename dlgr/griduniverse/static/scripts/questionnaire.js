/* global dallinger, console */
/*jshint esversion: 6 */

import { DIFIInput } from 'identityfusion';

$(document).ready(function() {

  // Initialize DIFI widget
  var $DIFI = $('input.DIFI-input'),
      spinner = dallinger.BusyForm();

  if ($DIFI.length) {
    var input = new DIFIInput(
      $DIFI.get(0),
      {
        groupLabel: $DIFI.attr('data-group-label'),
        groupImage: $DIFI.attr('data-group-image')
      }
    );
  }

  // Submit the questionnaire.
  $("#submit-questionnaire").click(function() {
    console.log("Submitting questionnaire.");
    var $elements = [$("form :input"), $(this)],
        questionSubmission = dallinger.submitQuestionnaire("questionnaire");

    spinner.freeze($elements);
    questionSubmission.done(dallinger.submitAssignment);
    questionSubmission.always(function () {
      spinner.unfreeze();
    });

  });

});
