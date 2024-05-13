# LogStream

Collect, Embed, and Query logs from anywhere. LogStream accept standard syslogs over UDP from clients, vectorizes the text, and stores it in Postgres ([pgvector](https://github.com/pgvector/pgvector)).

Sort and query your entire infrastructures logs with local LLMs! LogStream uses Ollama to interact with open-source LLM technology. LogStream can be used 
as part of your larger logging infrastructure, for example, use LogStream to collect syslogs from servers before passing them along to another service, or vice versa.

LogStream uses [Gradio](https://www.gradio.app/) to provide a simple web interface for querying logs.

![LogStream](./docs/screenshot-gradio.png)

## System Requirements
Storage: 20,000 log entries requires about 1GB of disk space.
RAM: The LogStream service run comfortably on smaller edge devices with 2GB of RAM, however you may need more if you expect large log queue bursts. 

LogStream requires an instance of [Ollama](https://ollama.com/) to run the default `nomic-embed-text` and `llama3` models. For best performance you want a 
supported GPU with at least ~12GB of VRAM. Otherwise you can use CPU acceleration, with ~12GB of system memory.

LogStream can queue thousands of logs per second, however the rate at which logs are processed will be limited by the embedding performance of the Ollama server, 
typically hundreds of logs per second. If you constantly send logs faster than your GPU or CPU can process the text embeddings without a break, your queue will grow indefinitely (until you run out of RAM), so keep an eye on the queue size!

Service clustering for performance scaling and HA is not supported yet, but it is on the roadmap.

## Running
LogStream is a work in progress! There is no authentication or official 
deployment method yet.

**TODO**

Create a .env file:
```env
```

To run LogStream:
```bash
docker compose up -d
```

## Sending Logs
LogStream accepts arbitrary strings as log messages over UDP port 41234. Typically this means you will bring a syslog client to send messages from a particular machine/server. See the `syslog-ng.conf` file for an example [syslog-ng](https://github.com/syslog-ng/syslog-ng) config file.

## Development Tips and Tricks

Rebuild and restart a single compose service:
```bash
docker compose up --build --force-recreate --no-deps webui -d
```