/*
  Contains the site specific js

*/

$(document).ready(function() {
  (function() {
      if (document.location.hash) {
          setTimeout(function() {
              window.scrollTo(window.scrollX, window.scrollY - 100);
          }, 10);
      }
  })();
  $(window).on("hashchange", function () {
      window.scrollTo(window.scrollX, window.scrollY - 100);
  });
  
});
