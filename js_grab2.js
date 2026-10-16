(function(){
  var ids = [], titles = [];
  // 抖音精选页: 视频卡片链接
  document.querySelectorAll('a').forEach(function(a){
    var m = (a.href||'').match(/\/video\/(\d{15,25})/);
    if (m && ids.indexOf(m[1])<0) ids.push(m[1]);
  });
  // 兜底: 页面文本里的 aweme_id 形态
  var html = document.documentElement.innerHTML;
  var m2 = html.match(/aweme_id[=:\s"']+(\d{15,25})/g);
  if (m2) m2.forEach(function(x){ var d=x.match(/(\d{15,25})/); if(d && ids.indexOf(d[1])<0) ids.push(d[1]); });
  return JSON.stringify({count: ids.length, ids: ids.slice(0,5), links: document.querySelectorAll('a[href*="/video/"]').length});
})()
