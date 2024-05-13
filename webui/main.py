import os
import requests
import json
import gradio as gr
import pandas as pd
import psycopg2

print("1")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
PORT = 5432
DB_NAME = "postgres"

API_URL = "http://app:3000"

conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}?port={PORT}&dbname={DB_NAME}"

conn = psycopg2.connect(conn_str)

print("2")

# table: logs (
#             id SERIAL PRIMARY KEY,
#             type VARCHAR(255) NOT NULL,
#             message TEXT NOT NULL,
#             timestamp TIMESTAMP NOT NULL,
#             source VARCHAR(255) NOT NULL,
#             embedding VECTOR(768)
#         );


def get_num_logs_per_hour():
    df = pd.read_sql(
        """
            SELECT date_trunc('hour', timestamp) AS hour, count(*) FROM logs
            WHERE timestamp > now() - interval '6 hours'
            GROUP BY hour;
        """,
        conn_str
    )

    print(df)
    return df

def embedding_search(query):
    # use api to search for embeddings /embed
    response = requests.post(f"{API_URL}/embed", json={"query": query})
    # as a string []
    response_str = str(response.json())
    print(response_str)


    curr = conn.cursor()
    curr.execute("SELECT type, message, timestamp, source FROM logs ORDER BY embedding <-> '{}' LIMIT 10".format(response_str))
    rows = curr.fetchall()
    return rows

def ask_llm(query):
    # first get the embedding using embedding_search
    logs = embedding_search(query)
    logs = json.dumps(logs, indent=4, sort_keys=True, default=str)
    
    latest_logs = get_latest_logs()
    latest_logs = json.dumps(latest_logs, indent=4, sort_keys=True, default=str)
    
    response = requests.post(f"{API_URL}/ask", json={"logs": logs, "query": query, "latest_logs": latest_logs})
    print(response.json())
    return str(response.json())
def query_results_ask_llm(frame):
    logs = json.dumps(frame, indent=4, sort_keys=True, default=str)
    response = requests.post(f"{API_URL}/ask", json={
        "latest_logs": logs,
        "logs": "",
        "query": "Please summarize the logs and provide insights."
    })
    return str(response.json())

def get_total_logs():
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM logs")
    rows = cur.fetchall()
    return rows[0][0]

def get_logs(query, option):
    cur = conn.cursor()
    if option == "sql":
        cur.execute(query)
    elif option == "search":
        cur.execute("SELECT type, message, timestamp, source FROM logs WHERE message LIKE '%{}%' ORDER BY timestamp DESC LIMIT 10".format(query))
    elif option == "embeddings_search":
        rows = embedding_search(query)
        return rows
    rows = cur.fetchall()
    print(rows)
    return rows
def get_latest_logs():
    cur = conn.cursor()
    cur.execute("SELECT type, message, timestamp, source FROM logs ORDER BY timestamp DESC LIMIT 100")
    rows = cur.fetchall()
    return rows

def get_queue_health():
    response = requests.get(f"{API_URL}/queue_health")
    return str(response.json())

print("3")

with gr.Blocks() as overview:
    with gr.Row():
        gr.Label("Logs Overview")
    with gr.Row():
        with gr.Column():
            gr.Label(value=get_total_logs, label="Total Logs", every = 2)
            gr.Label(value=get_queue_health, label="Queue Health", every = 2)
        gr.LinePlot(
            value = get_num_logs_per_hour,
            x="hour",
            y="count",
            width=800,
            every = 10
        )
    with gr.Row():
        with gr.Column():
            query = gr.Textbox(label="Query")
            option = gr.Radio(
                label="Select",
                choices=["search", "embeddings_search", "sql"],
                value="sql",
            )
            submit = gr.Button("Submit")
            gr.Label("Utilities")
            submit_latest = gr.Button("Get Latest Logs")

        with gr.Column():
            frame = gr.Dataframe(
                value=[],
                headers=["type", "message", "timestamp", "source"],
                datatype=["str", "str", "date", "str"],
            )
        submit.click(get_logs, inputs=[query, option], outputs=[frame], api_name="get_logs")
        submit_latest.click(get_latest_logs, outputs=[frame], api_name="get_latest_logs")
        # Once frame is updated, call the llm to explain the logs
    with gr.Row():
        llm_explain = gr.TextArea(label="LLM Explanation")
        frame.change(query_results_ask_llm, inputs=[frame], outputs=[llm_explain], api_name="query_results_ask_llm")

# Tab 2 - LLM Chat
with gr.Blocks() as llm_view:
    with gr.Row():
        gr.Label("Ask LLM")
    with gr.Row():
        with gr.Column():
            query_llm = gr.Textbox(label="Query")
            submit_llm = gr.Button("Submit")

        with gr.Column():
            res_llm = gr.TextArea(label="Response")
        submit_llm.click(ask_llm, inputs=[query_llm], outputs=[res_llm], api_name="ask_llm")   

# Tab 3 - Security Overview (ex. list all ssh attempts)

tabs = gr.TabbedInterface([overview, llm_view], title="Sineware LogStream")
tabs.launch(
    share=False,
    server_name="0.0.0.0"
)
