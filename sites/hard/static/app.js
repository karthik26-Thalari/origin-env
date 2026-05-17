// LEGACY BUG: old jQuery syntax
$(document).ready(function() {
  console.log("app.js loaded");

  // BUG: undeclaredVariable used in a loop -- causes repeated ReferenceError
  for (var i = 0; i < 5; i++) {
    console.log(undeclaredVariable[i]);
  }
});
