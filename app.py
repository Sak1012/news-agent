from __future__ import annotations

from flask import Flask, jsonify, request

from news_agent import AgentConfig, NewsAgent

app = Flask(__name__)
_agent = NewsAgent(AgentConfig.from_env())


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


@app.post("/news")
def fetch_news():
    payload = request.get_json(silent=True) or {}
    query = payload.get("query")
    limit = payload.get("limit")
    if not query:
        return jsonify({"error": "`query` is required"}), 400
    try:
        items = _agent.search(query=query, limit=limit)
        return jsonify([_agent.to_dict(item) for item in items])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - runtime guard
        app.logger.exception("Uncaught exception when handling /news")
        return jsonify({"error": "Unexpected server error", "detail": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8008)
