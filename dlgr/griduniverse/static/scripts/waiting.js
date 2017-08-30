/* global dallinger */

$(document).ready(function() {
    // wait for participant to be created and quorum to be reached
    dallinger.create_participant().done(function () {
        dallinger.goToPage("grid");
    });
});
