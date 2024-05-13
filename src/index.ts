import pg from 'pg';
import {Ollama} from 'ollama';
import Queue from 'bee-queue';
import express from 'express';
import dgram from 'node:dgram';
import { initExpress } from "./api/express";
const server = dgram.createSocket('udp4');

const pool = new pg.Pool({
    user: process.env.POSTGRES_USER,
    host: process.env.POSTGRES_HOST,
    database: process.env.POSTGRES_DB,
    password: process.env.POSTGRES_PASSWORD,
    port: parseInt(process.env.POSTGRES_PORT || "5432"),
});

const ollama = new Ollama({
    host: process.env.OLLAMA_HOST + ":" + process.env.OLLAMA_PORT,
});

const queue = new Queue('ollama', {
    redis: {
        host: 'valkey'
    }
});

server.on('error', (err: any) => {
  console.error(`server error:\n${err.stack}`);
  server.close();
});

server.on('message', async (msg: any, rinfo:any) => {
  queue.createJob({
    "type": "log",
    "message": msg.toString(),
    "timestamp": new Date().toISOString(),
    "source": rinfo.address + ":" + rinfo.port
  }).timeout(5000).save();

});

server.on('listening', async () => {
  const address = server.address();
  console.log(`Syslog ingest listening on ${address.address}:${address.port}`);
});

async function main() {
    // create a table if not exists
    // table: logs: type, message, timestamp, source
    const createTable = `
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            type VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            source VARCHAR(255) NOT NULL,
            embedding VECTOR(768)
        );
    `;
    await pool.query(createTable);

    console.log("Pulling " + process.env.EMBED_MODEL + " and " + process.env.QUERY_MODEL + " models from Ollama...");
    // pull embeddings model
    await ollama.pull({
        model: process.env.EMBED_MODEL as string,
    });
    // pull query model
    await ollama.pull({
        model: process.env.QUERY_MODEL as string,
    });


    queue.process(async (job: any, done: any) => {
        const embedding = await ollama.embeddings({
            model: "nomic-embed-text",
            prompt: job.data.message
        });
        await pool.query('INSERT INTO logs(type, message, timestamp, source, embedding) VALUES($1, $2, $3, $4, $5)', 
            [job.data.type, job.data.message, job.data.timestamp, job.data.source, JSON.stringify(embedding.embedding)]
        );
        done();
    });

    // periodically print the number of jobs in the queue
    setInterval(async () => {
        console.log("Queue length: ", await queue.checkHealth());
    }, 10000);

    // drop events older than DROP_EVENTS_OLDER_HOURS
    const DROP_EVENTS_OLDER_HOURS = parseInt(process.env.DROP_EVENTS_OLDER_HOURS || "0");
    if(DROP_EVENTS_OLDER_HOURS > 0) {
        setInterval(async () => {
            const dropQuery = `DELETE FROM logs WHERE timestamp < NOW() - INTERVAL '${DROP_EVENTS_OLDER_HOURS} hours';`;
            await pool.query(dropQuery);
        }, 1000 * 60 * 60);
    }

    server.bind(41234);

    const app = express()
    const port = 3000

    app.use(express.json());

    await initExpress(app, pool, ollama, queue);

    app.listen(port, () => {
        console.log(`API endpoints listening on ${port}`)
    })

}
main();