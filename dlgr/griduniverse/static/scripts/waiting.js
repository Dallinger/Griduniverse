/* global dallinger */

$(document).ready(function() {
    // wait for participant to be created and quorum to be reached
    dallinger.createParticipant().done(function () {
        if (skip_experiment) {
            $('.main_div').html('<p>The experiment has exceeded the maximum number of participants, your participation is not required. Click the button below to complete the HIT. You will be compensated as if you had completed the task.</p><button type="button" class="button btn-success">Complete</button>')
            $('.main_div button').on('click', submit_assignment);
        } else {
            dallinger.goToPage("grid");
        }
    });
});
