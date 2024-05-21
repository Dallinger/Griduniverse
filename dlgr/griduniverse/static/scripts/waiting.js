/* global dallinger */

$(document).ready(function () {
  // wait for participant to be created and quorum to be reached
  dallinger.createParticipant().done(function () {
    var difi = dallinger.getUrlParameter("DIFI_overlap"),
      spinner = dallinger.BusyForm();
    // are we coming from a pre DIFI question?
    // we have to handle it here because participant was just created
    if (difi) {
      console.log("Submitting questionnaire.");
      var formSerialized = $("form").serializeArray(),
        formDict = {},
        xhr,
        $elements = [$("form :input"), $(this)];

      formSerialized.forEach(function (field) {
        formDict[field.name] = field.value;
      });

      xhr = dallinger.post("/question/" + dallinger.identity.participantId, {
        question: "Pre DIFI",
        number: 1,
        response: JSON.stringify(formDict),
      });

      spinner.freeze($elements);
      xhr.done(function () {
        dallinger.goToPage("grid");
      });
      xhr.always(function () {
        spinner.unfreeze();
      });
    } else {
      dallinger.goToPage("grid");
    }
  });
});
