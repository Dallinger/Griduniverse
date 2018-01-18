/* global dallinger */

$(document).ready(function() {
  // Begin the experiment.
  $("#begin-experiment").click(function() {
    window.location.href = next_location;
  });

  // Opt out of the experiment.
  $("#opt-out").click(function() {
    window.location.href = "/questionnaire?participant_id=" + dallinger.identity.participantId;
  });
});
