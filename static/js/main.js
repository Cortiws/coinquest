// بروزرسانی کوین از سرور (اختیاری)
function updateCoins() {
    fetch('/api/user_coins').then(res => res.json()).then(data => {
        document.getElementById('coin-count').textContent = data.coins;
    });
}
setInterval(updateCoins, 30000);  // هر ۳۰ ثانیه
