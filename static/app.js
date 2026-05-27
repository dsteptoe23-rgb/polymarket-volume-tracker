document.getElementById('analyzeBtn').addEventListener('click', analyzeMarkets);

function analyzeMarkets() {
    const categories = document.getElementById('categories').value;
    const top_n = document.getElementById('top_n').value;
    const multiplier = document.getElementById('multiplier').value;
    const resultsDiv = document.getElementById('results');
    const btn = document.getElementById('analyzeBtn');

    console.log('Starting analysis...');
    resultsDiv.innerHTML = '<div class="loading">⏳ Fetching and analyzing markets... This may take a moment.</div>';
    btn.disabled = true;

    fetch('/api/analyze?categories=' + encodeURIComponent(categories) + '&top_n=' + top_n + '&multiplier=' + multiplier)
        .then(response => response.json())
        .then(data => {
            console.log('Data:', data);
            
            if (data.error) {
                resultsDiv.innerHTML = '<div class="error">❌ API Error: ' + data.error + '</div>';
                btn.disabled = false;
                return;
            }

            let html = '<div class="summary">';
            html += '<strong>📈 Searched:</strong> ' + (data.total_markets_searched || 0).toLocaleString() + ' markets | ';
            html += '<strong>✅ Matches:</strong> ' + (data.matches_found || 0) + ' | ';
            html += '<strong>🚨 Alerts:</strong> ' + (data.alerts || 0);
            html += '</div>';

            if (!data.results || data.results.length === 0) {
                html += '<div class="info">No matching markets found for the given keywords.</div>';
            } else {
                data.results.forEach(market => {
                    html += buildMarketCard(market);
                });
            }
            
            resultsDiv.innerHTML = html;
            btn.disabled = false;
        })
        .catch(error => {
            console.error('Error:', error);
            resultsDiv.innerHTML = '<div class="error">❌ Error: ' + error.message + '</div>';
            btn.disabled = false;
        });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function buildOutcomesTable(outcomes) {
    if (!outcomes || outcomes.length === 0) {
        return '<div style="padding: 30px; text-align: center; color: #999;">Outcome data not available</div>';
    }
    
    let rows = '';
    outcomes.forEach(o => {
        const outcomeName = escapeHtml(o.outcome || 'N/A');
        const volume = (o.volume_24hr || 0).toLocaleString();
        const price = ((o.price || 0) * 100).toFixed(1);
        
        rows += '<tr>';
        rows += '<td class="outcome-name">' + outcomeName + '</td>';
        rows += '<td style="text-align: right; color: #666;">$' + volume + '</td>';
        rows += '<td style="text-align: right;"><span class="price-tag">' + price + '¢</span></td>';
        rows += '</tr>';
    });
    
    let table = '<table class="outcomes-table">';
    table += '<thead><tr><th>Outcome</th><th style="text-align: right;">Volume (24h)</th><th style="text-align: right;">Price</th></tr></thead>';
    table += '<tbody>' + rows + '</tbody>';
    table += '</table>';
    
    return table;
}

function buildMarketCard(market) {
    const alertClass = market.has_alert ? 'alert' : '';
    const alertBadge = market.has_alert ? '<span class="alert-badge">🚨 VOLUME SPIKE</span>' : '';
    
    const marketName = escapeHtml(market.market_name || 'Unknown Market');
    const marketUrl = market.polymarket_url || '#';
    
    const outcomesHtml = buildOutcomesTable(market.outcomes);
    
    const mult7d = market.multiplier_7d || 0;
    const mult30d = market.multiplier_30d || 0;
    const mult7dClass = mult7d >= 2.0 ? 'multiplier-highlight' : '';
    const mult30dClass = mult30d >= 2.0 ? 'multiplier-highlight' : '';

    let card = '<div class="market-card ' + alertClass + '">';
    card += '<div class="market-header">';
    card += '<div class="market-title">' + marketName + ' ' + alertBadge + '</div>';
    card += '<a href="' + marketUrl + '" target="_blank" rel="noopener noreferrer" class="market-link">📊 View on Polymarket →</a>';
    card += '</div>';
    card += '<div class="market-body">';
    card += outcomesHtml;
    card += '<div class="volume-stats">';
    card += '<div class="stat-box"><div class="stat-label">24hr Volume</div><div class="stat-value">$' + (market.volume_today || 0).toLocaleString() + '</div></div>';
    card += '<div class="stat-box"><div class="stat-label">7d Average</div><div class="stat-value">$' + (market.avg_7d || 0).toLocaleString() + '</div></div>';
    card += '<div class="stat-box"><div class="stat-label">7d Multiplier</div><div class="stat-value ' + mult7dClass + '">' + mult7d.toFixed(2) + 'x</div></div>';
    card += '<div class="stat-box"><div class="stat-label">30d Average</div><div class="stat-value">$' + (market.avg_30d || 0).toLocaleString() + '</div></div>';
    card += '<div class="stat-box"><div class="stat-label">30d Multiplier</div><div class="stat-value ' + mult30dClass + '">' + mult30d.toFixed(2) + 'x</div></div>';
    card += '</div>';
    card += '</div>';
    card += '</div>';
    
    return card;
}
