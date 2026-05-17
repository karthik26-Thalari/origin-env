// FIX: removed all jQuery -- using vanilla JS only
// FIX: removed undeclaredVariable reference -- no more ReferenceError

document.addEventListener("DOMContentLoaded", function() {
  console.log("app.js loaded cleanly -- no errors");
});

// FIX: vanilla JS fetch replacing jQuery ajax
function callApi() {
  fetch("/api/data")
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var el = document.getElementById("api-result");
      if (el) el.textContent = "Result: " + data.result;
    })
    .catch(function(e) {
      var el = document.getElementById("api-result");
      if (el) el.textContent = "Error: " + e;
    });
}
