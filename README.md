# LLM Labeling UI

![LLM Labeling UI](./public/screenshot.png)

## About

**WARNIN** This project is for my personal use and is still under development. I am not responsible for any data loss that may occur during your use.

LLM Labeling UI is a project fork from [Chatbot UI](https://github.com/mckaywrigley/chatbot-ui), and made the following modifications to make it more suitable for large language model data labeling tasks.

- The backend code is implemented in python, the frontend code is precompiled, so it can run without a nodejs environment
- The Chatbot UI uses localStorage to save data, with a size limit of 5MB, the LLM Labeling UI can load local data when starting the service, with no size limit
- Web interaction:
  - You can view data in pages
  - You can directly modify/delete model's response results
  - A confirmation button has been added before deleting the conversation message
  - Display the number of messages in the current dialogue, token length
  - You can modify the system prompt during the dialogue

## Quick Start

```bash
pip install llm-labeling-ui
```

**1. Provide OpenAI API Key**

You can provide openai api key before start server or configure it later in the web page.

```bash
export OPENAI_API_KEY=YOUR_KEY
export OPENAI_ORGANIZATION=YOUR_ORG
```

**2. Start Server**

```bash
llm-labeling-ui start --history-file chatbot-ui-v4-format-history.json --tokenizer meta-llama/Llama-2-7b
```

- Before the service starts, a `chatbot-ui-v4-format-history.sqlite` file will be created based on `chatbot-ui-v4-format-history.json`. All your modifications on the page will be saved into the sqlite file. If the `chatbot-ui-v4-format-history.sqlite` file already exists, it will be automatically read.
- `--tokenizer` is used to display how many tokens the current conversation on the webpage contains. Please note that this is not the token consumed by calling the openai api.

**3. Export data from sqlite**

```bash
llm-labeling-ui export --db-path chatbot-ui-v4-format-history.sqlite
```

By default exported data will be generated in the same directory as `db_path``, and the file name will be added with a timestam.
