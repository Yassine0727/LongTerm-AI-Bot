from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

HISTORY_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Price History</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:#0a0a0a; color:#e5e5e5; font-family:Arial; padding:20px; }
        .container { max-width:1400px; margin:0 auto; }
        .header {
            background:#1a1a1a; padding:20px 30px; border-radius:12px;
            border:1px solid #333; display:flex; justify-content:space-between;
            align-items:center; flex-wrap:wrap; margin-bottom:25px;
        }
        .header h1 { color:#f7931a; }
        .back-btn {
            padding:10px 24px; border:none; border-radius:8px;
            background:#1e3a5f; color:#60a5fa; cursor:pointer;
            font-weight:bold; text-decoration:none;
        }
        .back-btn:hover { background:#1e40af; }
        .grid-2 { display:grid; grid-template-columns:2fr 1fr; gap:20px; margin-bottom:20px; }
        @media (max-width:768px) { .grid-2 { grid-template-columns:1fr; } }
        .card { background:#1a1a1a; border-radius:12px; padding:20px; border:1px solid #2a2a2a; }
        .card-title { font-size:13px; color:#888; text-transform:uppercase; margin-bottom:12px; }
        .chart-container { background:#0a0a0a; padding:15px; border-radius:8px; border:1px solid #222; }
        #priceChart { height:400px; width:100%; }
        .stat-box { background:#0a0a0a; padding:15px; border-radius:8px; border:1px solid #222; }
        .stat-row { display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px solid #111; }
        .stat-row:last-child { border-bottom:none; }
        .stat-label { color:#666; font-size:13px; }
        .stat-value { font-weight:bold; }
        .stat-value.positive { color:#34d399; }
        .stat-value.negative { color:#f87171; }
        .stat-value.neutral { color:#fbbf24; }
        .table-container { overflow-x:auto; margin-top:10px; max-height:400px; overflow-y:auto; }
        table { width:100%; border-collapse:collapse; font-size:13px; }
        table th { background:#1a1a1a; color:#888; padding:10px 12px; text-align:left; border-bottom:2px solid #333; position:sticky; top:0; }
        table td { padding:8px 12px; border-bottom:1px solid #222; color:#ccc; }
        table tr:hover td { background:#1a1a1a; }
        .controls { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:15px; align-items:center; }
        .controls select { padding:8px 14px; border-radius:8px; border:1px solid #333; background:#0a0a0a; color:white; font-size:13px; }
        .controls button { padding:8px 20px; border:none; border-radius:8px; background:#1e3a5f; color:#60a5fa; cursor:pointer; font-weight:bold; }
        .controls button:hover { background:#1e40af; }
        .summary-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-top:15px; }
        @media (max-width:600px) { .summary-grid { grid-template-columns:repeat(3,1fr); } }
        .summary-item { text-align:center; padding:10px; background:#0a0a0a; border-radius:8px; border:1px solid #222; }
        .summary-item .label { color:#666; font-size:11px; }
        .summary-item .value { font-size:18px; font-weight:bold; margin-top:4px; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>Price History</h1>
        <a href="/web" class="back-btn">Back to Dashboard</a>
    </div>

    <div class="card">
        <div class="card-title">Controls</div>
        <div class="controls">
            <select id="histAsset">
                <option value="BTC">BTC</option>
                <option value="ETH">ETH</option>
                <option value="GOLD">GOLD</option>
            </select>
            <select id="histPeriod">
                <option value="7">7 days</option>
                <option value="14">14 days</option>
                <option value="30" selected>30 days</option>
                <option value="90">90 days</option>
                <option value="180">180 days</option>
                <option value="365">1 year</option>
            </select>
            <button onclick="loadHistoryPage()">Refresh</button>
        </div>
    </div>

    <div class="grid-2">
        <div class="card">
            <div class="card-title">Price Chart</div>
            <div class="chart-container">
                <canvas id="priceChart"></canvas>
            </div>
        </div>
        <div class="card">
            <div class="card-title">Statistics</div>
            <div class="stat-box" id="statsBox">
                <div class="stat-row"><span class="stat-label">Current</span><span class="stat-value positive" id="sCurrent">-</span></div>
                <div class="stat-row"><span class="stat-label">Highest</span><span class="stat-value positive" id="sHigh">-</span></div>
                <div class="stat-row"><span class="stat-label">Lowest</span><span class="stat-value negative" id="sLow">-</span></div>
                <div class="stat-row"><span class="stat-label">Average</span><span class="stat-value neutral" id="sAvg">-</span></div>
                <div class="stat-row"><span class="stat-label">Change</span><span class="stat-value" id="sChange">-</span></div>
                <div class="stat-row"><span class="stat-label">Records</span><span class="stat-value" id="sRecords">-</span></div>
            </div>
            <div class="summary-grid" id="summaryGrid">
                <div class="summary-item"><div class="label">Open</div><div class="value" id="sumOpen">-</div></div>
                <div class="summary-item"><div class="label">Close</div><div class="value" id="sumClose">-</div></div>
                <div class="summary-item"><div class="label">High</div><div class="value" id="sumHigh">-</div></div>
                <div class="summary-item"><div class="label">Low</div><div class="value" id="sumLow">-</div></div>
                <div class="summary-item"><div class="label">Change</div><div class="value" id="sumChange">-</div></div>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-title">Data Table</div>
        <div class="table-container" id="tableContainer">
            <div style="color:#444;text-align:center;padding:30px;">Loading...</div>
        </div>
    </div>
</div>

<script>
var priceChart = null;

async function callAPI(endpoint) {
    try {
        var response = await fetch(endpoint, {
            headers: { 'password': 'admin123' }
        });
        if (!response.ok) return null;
        return await response.json();
    } catch(e) { return null; }
}

async function loadHistoryPage() {
    var asset = document.getElementById('histAsset').value;
    var period = parseInt(document.getElementById('histPeriod').value);
    
    document.getElementById('tableContainer').innerHTML = '<div style="color:#444;text-align:center;padding:30px;">Loading...</div>';
    
    var data = await callAPI('/api/price-history');
    if (!data || !data.success) {
        document.getElementById('tableContainer').innerHTML = '<div style="color:#f87171;text-align:center;padding:30px;">Error</div>';
        return;
    }
    
    var history = data.history || [];
    if (history.length === 0) {
        document.getElementById('tableContainer').innerHTML = '<div style="color:#444;text-align:center;padding:30px;">No records yet.</div>';
        return;
    }
    
    var cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - period);
    
    var records = [];
    for (var i = history.length - 1; i >= 0; i--) {
        var r = history[i];
        var recordDate = new Date(r.timestamp);
        if (recordDate >= cutoff) {
            var price = r.prices && r.prices[asset] ? r.prices[asset].price : null;
            if (price > 0) {
                records.push({
                    date: r.date,
                    time: r.time,
                    timestamp: r.timestamp,
                    price: price,
                    change: r.prices[asset].change_24h || 0,
                    volume: r.prices[asset].volume || 0
                });
            }
        }
    }
    
    records.reverse();
    
    if (records.length === 0) {
        document.getElementById('tableContainer').innerHTML = '<div style="color:#444;text-align:center;padding:30px;">No data for this period</div>';
        return;
    }
    
    var prices = records.map(function(r) { return r.price; });
    var current = prices[prices.length - 1] || 0;
    var high = Math.max.apply(null, prices) || 0;
    var low = Math.min.apply(null, prices) || 0;
    var avg = prices.reduce(function(a,b){return a+b;},0) / prices.length || 0;
    var first = prices[0] || 0;
    var change = first > 0 ? ((current - first) / first) * 100 : 0;
    
    var changeEl = document.getElementById('sChange');
    changeEl.textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
    changeEl.className = 'stat-value ' + (change >= 0 ? 'positive' : 'negative');
    
    document.getElementById('sCurrent').textContent = '$' + current.toFixed(2);
    document.getElementById('sHigh').textContent = '$' + high.toFixed(2);
    document.getElementById('sLow').textContent = '$' + low.toFixed(2);
    document.getElementById('sAvg').textContent = '$' + avg.toFixed(2);
    document.getElementById('sRecords').textContent = records.length;
    
    document.getElementById('sumOpen').textContent = '$' + first.toFixed(2);
    document.getElementById('sumClose').textContent = '$' + current.toFixed(2);
    document.getElementById('sumHigh').textContent = '$' + high.toFixed(2);
    document.getElementById('sumLow').textContent = '$' + low.toFixed(2);
    document.getElementById('sumChange').textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
    document.getElementById('sumChange').style.color = change >= 0 ? '#34d399' : '#f87171';
    
    var html = '<table><thead><tr><th>Date</th><th>Time</th><th>Price</th><th>24h</th><th>Volume</th></tr></thead><tbody>';
    for (var i = records.length - 1; i >= 0; i--) {
        var r = records[i];
        var cls = r.change > 0 ? 'positive' : (r.change < 0 ? 'negative' : 'neutral');
        html += '<tr><td>' + r.date + '</td><td>' + r.time + '</td><td>$' + r.price.toFixed(2) + '</td><td class="' + cls + '">' + (r.change > 0 ? '+' : '') + r.change.toFixed(2) + '%</td><td>' + (r.volume > 0 ? r.volume.toFixed(0) : '-') + '</td></tr>';
    }
    html += '</tbody></table>';
    document.getElementById('tableContainer').innerHTML = html;
    
    var ctx = document.getElementById('priceChart').getContext('2d');
    var labels = records.map(function(r) {
        var d = new Date(r.timestamp);
        return d.getDate() + '/' + (d.getMonth() + 1);
    });
    var pricesData = records.map(function(r) { return r.price; });
    
    var color = asset === 'BTC' ? '#f7931a' : asset === 'ETH' ? '#627EEA' : '#ffd700';
    var gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, color + '33');
    gradient.addColorStop(1, color + '00');
    
    if (priceChart) { priceChart.destroy(); }
    
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: asset + ' Price',
                data: pricesData,
                borderColor: color,
                backgroundColor: gradient,
                fill: true,
                tension: 0.3,
                pointRadius: 2,
                pointBackgroundColor: color,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#888', font: { size: 12 } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return '$' + context.parsed.y.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: '#1a1a1a', drawBorder: false },
                    ticks: { color: '#666', font: { size: 10 }, maxTicksLimit: 20 }
                },
                y: {
                    grid: { color: '#1a1a1a', drawBorder: false },
                    ticks: {
                        color: '#666',
                        font: { size: 10 },
                        callback: function(value) { return '$' + value.toFixed(0); }
                    }
                }
            }
        }
    });
}

loadHistoryPage();
</script>
</body>
</html>
'''

@router.get("/history")
async def history_page():
    return HTMLResponse(HISTORY_HTML)