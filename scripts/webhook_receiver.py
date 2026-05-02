from flask import Flask, request
import requests
import base64

app = Flask(__name__)

AIRFLOW_URL  = "http://localhost:8082"
AIRFLOW_USER = "admin"
AIRFLOW_PASS = "admin123"
DAG_ID       = "training_pipeline"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    ref  = data.get("ref", "")
    print(f"Push received on: {ref}")

    token = base64.b64encode(f"{AIRFLOW_USER}:{AIRFLOW_PASS}".encode()).decode()
    resp  = requests.post(
        f"{AIRFLOW_URL}/api/v1/dags/{DAG_ID}/dagRuns",
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Basic {token}",
        },
        json={"conf": {"triggered_by": "github_webhook", "ref": ref}},
    )
    print(f"Airflow response: {resp.status_code} {resp.text}")
    return {"status": "triggered", "airflow": resp.status_code}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
