(function(){
  var ids = [];
  document.querySelectorAll('a[href*="/video/"]').forEach(function(a){
    var m = a.href.match(/\/video\/(\d+)/);
    if (m) ids.push(m[1]);
  });
  return JSON.stringify({count: ids.length, ids: ids.slice(0,5), url: location.href});
})()
