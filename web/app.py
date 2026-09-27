"""
Flask Web Application & REST API Server
Provides endpoints for market data, trading execution,
portfolio performance tracking, and live simulation feeds.
"""

import os
import json
from flask import Flask, render_template, jsonify, request, send_file
from engine.trading_engine import TradingEngine

# Initialize Flask application with explicit template and static paths
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))

app = Flask(
    __name__,
    template_folder=template_dir,
    static_folder=static_dir,
    static_url_path="/static",
)

# Global Trading Engine instance
engine = TradingEngine()


@app.route("/")
def index():
    """Renders the main trading terminal application."""
    return render_template("index.html")


@app.route("/api/market", methods=["GET"])
def get_market():
    """Fetches real-time market data for all listed stocks and index stats."""
    return jsonify(engine.get_market_state())


@app.route("/api/market/tick", methods=["POST"])
def tick_market():
    """Advances market simulation by requested steps."""
    data = request.get_json(silent=True) or {}
    steps = int(data.get("steps", 1))
    market_state = engine.tick_market(steps)
    return jsonify({
        "success": True,
        "message": f"Market advanced {steps} tick(s).",
        "market": market_state,
        "portfolio": engine.get_portfolio_state(),
    })


@app.route("/api/market/sentiment", methods=["POST"])
def set_sentiment():
    """Updates market sentiment regime."""
    data = request.get_json(silent=True) or {}
    sentiment = data.get("sentiment", "neutral")
    success = engine.set_market_sentiment(sentiment)
    return jsonify({
        "success": success,
        "sentiment": engine.market.sentiment,
        "label": engine.market.SENTIMENT_PROFILES.get(engine.market.sentiment, {}).get("label"),
    })


@app.route("/api/stock/<symbol>", methods=["GET"])
def get_stock(symbol):
    """Fetches single stock quote with complete price history."""
    stock = engine.market.get_stock(symbol)
    if not stock:
        return jsonify({"error": f"Stock '{symbol}' not found."}), 404
    return jsonify(stock.to_dict(include_history=True))


@app.route("/api/portfolio", methods=["GET"])
def get_portfolio():
    """Returns active user's portfolio, holdings, P&L, and performance history."""
    return jsonify(engine.get_portfolio_state())


@app.route("/api/trade/buy", methods=["POST"])
def execute_buy():
    """Executes a buy order."""
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol", "")
    try:
        quantity = int(data.get("quantity", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid share quantity."}), 400

    success, msg, tx = engine.buy_stock(symbol, quantity)
    status_code = 200 if success else 400
    return jsonify({
        "success": success,
        "message": msg,
        "transaction": tx.to_dict() if tx else None,
        "portfolio": engine.get_portfolio_state(),
    }), status_code


@app.route("/api/trade/sell", methods=["POST"])
def execute_sell():
    """Executes a sell order."""
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol", "")
    try:
        quantity = int(data.get("quantity", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid share quantity."}), 400

    success, msg, tx = engine.sell_stock(symbol, quantity)
    status_code = 200 if success else 400
    return jsonify({
        "success": success,
        "message": msg,
        "transaction": tx.to_dict() if tx else None,
        "portfolio": engine.get_portfolio_state(),
    }), status_code


@app.route("/api/user/deposit", methods=["POST"])
def deposit_cash():
    """Deposits funds into active user account."""
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount", 0.0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid deposit amount."}), 400

    success, msg = engine.deposit_cash(amount)
    status_code = 200 if success else 400
    return jsonify({
        "success": success,
        "message": msg,
        "portfolio": engine.get_portfolio_state(),
    }), status_code


@app.route("/api/user/switch", methods=["POST"])
def switch_user():
    """Switches or registers a new user profile."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    display_name = data.get("display_name", "").strip() or None

    if not username:
        return jsonify({"success": False, "message": "Username is required."}), 400

    engine.set_active_user(username, display_name)
    return jsonify({
        "success": True,
        "message": f"Active user switched to {engine.active_user.display_name}.",
        "portfolio": engine.get_portfolio_state(),
    })


@app.route("/api/watchlist/toggle", methods=["POST"])
def toggle_watchlist():
    """Toggles favorite stock in user's watchlist."""
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol", "")
    is_in_watchlist = engine.toggle_watchlist(symbol)
    return jsonify({
        "success": True,
        "symbol": symbol.upper(),
        "in_watchlist": is_in_watchlist,
        "watchlist": engine.active_user.watchlist,
    })


@app.route("/api/export", methods=["GET"])
def export_portfolio():
    """Downloads active user's portfolio and transaction data as JSON."""
    filename = f"export_{engine.active_user.username}.json"
    filepath = os.path.join("data", filename)
    engine.export_data(filepath)
    if os.path.exists(filepath):
        return send_file(
            filepath,
            as_attachment=True,
            download_name=f"{engine.active_user.username}_portfolio.json",
            mimetype="application/json",
        )
    return jsonify({"error": "Failed to create export file."}), 500


@app.route("/api/import", methods=["POST"])
def import_portfolio():
    """Imports portfolio data from uploaded JSON."""
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected."}), 400

    try:
        temp_path = os.path.join("data", "temp_import.json")
        file.save(temp_path)
        success, msg = engine.import_data(temp_path)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({
            "success": success,
            "message": msg,
            "portfolio": engine.get_portfolio_state(),
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def create_app():
    """App factory function."""
    return app


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
