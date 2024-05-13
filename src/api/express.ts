import { Express } from 'express'
import { Ollama } from 'ollama'
import pg from 'pg'
export async function initExpress(app: Express, pool: pg.Pool, ollama: Ollama, queue: any) {
    app.post('/embed', async (req, res) => {
        const query = req.body.query;
        console.log(req.body);
        let embed = await ollama.embeddings({
            model: "nomic-embed-text",
            prompt: query as string,
        });
        res.json(embed.embedding);
    });
    app.post('/ask', async (req, res) => {
        const {
            query,
            logs,
            latest_logs
        } = req.body;
        console.log(req.body);
        const prompt = "The current date and time is: " + new Date() +
        "-> Latest Logs: \n" + latest_logs +
        "-> Other Logs Potentially Related to the Query: \n" + logs +
        "\n\nQuestion: " + query;
        console.log("Prompt: " + prompt);   

        let response = await ollama.generate({
            model: "llama3:8b-instruct-q8_0",
            system: "You are a helpful assistant that reviews syslog output from servers. You are asked to provide a summary of the logs considering DevOps, SysOps and Cybersecurity perspectives.",
            prompt: prompt,
            stream: false
        });
        console.log("Cooked up answer: " + response.response);
        res.json(response.response);
    });
    app.get('/queue_health', async (req, res) => {
        const jobs = await queue.checkHealth();
        res.json(jobs);
    });
}