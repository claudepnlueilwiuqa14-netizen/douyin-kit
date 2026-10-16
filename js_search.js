(function(){
  var cards = document.querySelectorAll('[data-e2e="search-card"], .search-result-card, [class*="search-result"]');
  var txt = document.body ? document.body.innerText : '';
  return JSON.stringify({
    url: location.href,
    cards: cards.length,
    loginGate: txt.indexOf('扫码登录')>=0,
    head: txt.slice(0, 200)
  });
})()
