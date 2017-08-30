$(document).ready(function() {
  // Print the consent form.
  $("#print-consent").click(function() {
    console.log("hello");
    window.print();
  });

  // Consent to the experiment.
  $("#consent").click(function() {
    store.set("hit_id", dallinger.getUrlParameter("hit_id"));
    store.set("worker_id", dallinger.getUrlParameter("worker_id"));
    store.set("assignment_id", dallinger.getUrlParameter("assignment_id"));
    store.set("mode", dallinger.getUrlParameter("mode"));

    window.location.href = "/instructions";
  });

  // Consent to the experiment.
  $("#no-consent").click(function() {
    self.close();
  });
});
