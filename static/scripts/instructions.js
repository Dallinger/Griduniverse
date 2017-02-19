$(document).ready(function() {
  // Begin the experiment.
  $("#begin-experiment").click(function() {
    allow_exit();
    window.location.href = "/grid";
  });

  // Opt out of the experiment.
  $("#opt-out").click(function() {
    allow_exit();
    window.location.href = "/questionnaire";
  });
});
