$(document).ready(function() {
    // Begin the experiment.
    $("#begin-experiment").click(function() {
        allow_exit();
        window.location.href = '/grid';
    });
});
