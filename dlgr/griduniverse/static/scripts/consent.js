$(document).ready(function() {
  // Print the consent form.
  $("#print-consent").click(function() {
    console.log("hello");
    window.print();
  });

  // Consent to the experiment.
  $("#consent").click(function() {
    dallinger.goToPage("instructions");
  });

  // Consent to the experiment.
  $("#no-consent").click(function() {
    self.close();
  });
});
