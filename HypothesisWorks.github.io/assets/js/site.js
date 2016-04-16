/*
  Contains the site specific js

*/

$(document).ready(function() {

  $(window).on("hashchange", function () {
      window.scrollTo(window.scrollX, window.scrollY - 100);
  });
  
});
