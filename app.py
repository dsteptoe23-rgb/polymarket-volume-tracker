from flask import Flask, render_template, request, jsonify
import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze')
def analyze():
    try:
        categories = request.args.get('categories', 'trump,election').lower()
        top_n = int(request.args.get('top_n', 100))
        multiplier_threshold = float(request.args.get('multiplier', 2.0))

        keywords = [k.strip() for k in categories.split(',') if k.strip()]
        
        print(f"\n{'='*80}")
        print(f"Searching for keywords: {keywords}")
        print(f"{'='*80}\n")

        # Fetch ALL active markets
        all_markets = []
        offset = 0
        limit = 100
        max_pages = 10
        
        for page in range(max_pages):
            try:
                events_response = requests.get(
                    f"{GAMMA_API}/events",
                    params={
                        'closed': 'false',
                        'limit': limit,
                        'offset': offset
                    },
                    timeout=20
                )
                
                if events_response.status_code != 200:
                    break
                
                events_data = events_response.json()
                
                if not isinstance(events_data, list) or len(events_data) == 0:
                    break
                
                for event in events_data:
                    if isinstance(event, dict) and 'markets' in event:
                        event_slug = event.get('slug', '')
                        
                        markets = event.get('markets', [])
                        if isinstance(markets, list):
                            for market in markets:
                                if isinstance(market, dict):
                                    is_active = market.get('active', False)
                                    is_closed = market.get('closed', True)
                                    
                                    if is_active and not is_closed:
                                        market['_event_slug'] = event_slug
                                        all_markets.append(market)
                
                if len(events_data) < limit:
                    break
                
                offset += limit
                
            except Exception as e:
                print(f"Error fetching page {page+1}: {e}")
                break

        print(f"✅ Total active markets: {len(all_markets)}\n")

        # Filter by keywords
        matching_markets = []
        for market in all_markets:
            if not isinstance(market, dict):
                continue
            
            question = market.get('question', '')
            if not isinstance(question, str):
                continue
                
            if any(kw in question.lower() for kw in keywords):
                matching_markets.append(market)

        print(f"✅ Matching markets: {len(matching_markets)}\n")

        results = []
        alert_count = 0
        processed_count = 0
        skipped_no_volume = 0

        # Process markets
        for idx, market in enumerate(matching_markets[:top_n]):
            try:
                question = market.get('question', 'Unknown')
                condition_id = market.get('conditionId')
                event_slug = market.get('_event_slug', '')
                
                if not condition_id:
                    continue

                # Get volume fields
                volume_24h_raw = market.get('volume24hr')
                volume_1wk_raw = market.get('volume1wk') or market.get('volume1wkClob')
                volume_1mo_raw = market.get('volume1mo') or market.get('volume1moClob')
                
                # Convert to float, treating None as 0
                volume_24h = float(volume_24h_raw) if volume_24h_raw is not None else 0
                volume_1wk = float(volume_1wk_raw) if volume_1wk_raw is not None else 0
                volume_1mo = float(volume_1mo_raw) if volume_1mo_raw is not None else 0
                
                # Skip if no 24hr volume
                if volume_24h <= 0:
                    skipped_no_volume += 1
                    continue

                processed_count += 1

                # Calculate averages
                avg_7d = volume_1wk / 7 if volume_1wk > 0 else volume_24h
                avg_30d = volume_1mo / 30 if volume_1mo > 0 else volume_24h

                mult_7d = volume_24h / avg_7d if avg_7d > 0 else 0
                mult_30d = volume_24h / avg_30d if avg_30d > 0 else 0

                has_alert = mult_7d >= multiplier_threshold or mult_30d >= multiplier_threshold
                
                if has_alert:
                    alert_count += 1
                    print(f"🚨 ALERT: {question[:60]}")
                    print(f"   Vol 24h: ${volume_24h:,.2f} | Mult 7d: {mult_7d:.2f}x | Mult 30d: {mult_30d:.2f}x")

                # Get outcomes and prices - PARSE JSON STRINGS
                outcomes = []
                clob_token_ids_raw = market.get('clobTokenIds', [])
                outcome_names_raw = market.get('outcomes', [])
                outcome_prices_raw = market.get('outcomePrices', [])
                
                # Parse if they're JSON strings
                if isinstance(clob_token_ids_raw, str):
                    try:
                        clob_token_ids = json.loads(clob_token_ids_raw)
                    except:
                        clob_token_ids = []
                else:
                    clob_token_ids = clob_token_ids_raw
                
                if isinstance(outcome_names_raw, str):
                    try:
                        outcome_names = json.loads(outcome_names_raw)
                    except:
                        outcome_names = []
                else:
                    outcome_names = outcome_names_raw
                
                if isinstance(outcome_prices_raw, str):
                    try:
                        outcome_prices = json.loads(outcome_prices_raw)
                    except:
                        outcome_prices = []
                else:
                    outcome_prices = outcome_prices_raw

                for i, outcome_name in enumerate(outcome_names):
                    price = 0
                    if i < len(outcome_prices):
                        try:
                            price = float(outcome_prices[i])
                        except:
                            price = 0

                    outcomes.append({
                        'outcome': outcome_name,
                        'volume_24hr': round(volume_24h / len(outcome_names), 2) if outcome_names else round(volume_24h, 2),
                        'price': price
                    })

                results.append({
                    'market_name': question,
                    'polymarket_url': f"https://polymarket.com/event/{event_slug}",
                    'volume_today': round(volume_24h, 2),
                    'avg_7d': round(avg_7d, 2),
                    'avg_30d': round(avg_30d, 2),
                    'multiplier_7d': round(mult_7d, 2),
                    'multiplier_30d': round(mult_30d, 2),
                    'has_alert': has_alert,
                    'outcomes': outcomes
                })

            except Exception as e:
                print(f"Error processing market: {e}")
                continue

        # Sort by highest multiplier
        results.sort(key=lambda x: max(x['multiplier_7d'], x['multiplier_30d']), reverse=True)

        print(f"\n{'='*80}")
        print(f"✅ DONE:")
        print(f"   Processed: {processed_count} markets with volume")
        print(f"   Skipped: {skipped_no_volume} markets (no volume)")
        print(f"   Alerts: {alert_count}")
        print(f"   Results: {len(results)}")
        print(f"{'='*80}\n")

        return jsonify({
            'total_markets_searched': len(all_markets),
            'matches_found': len(results),
            'alerts': alert_count,
            'results': results
        })

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*80)
    print("POLYMARKET VOLUME TRACKER")
    print("="*80)
    print("Server will be accessible to others on your network")
    print("="*80 + "\n")
    
    # Make accessible to others on your network
    app.run(host='0.0.0.0', port=5000, debug=True)