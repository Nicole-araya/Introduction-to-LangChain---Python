# LangChain Academy: Introduction to LangChain (Python) 🦜🔗

This repository contains my personal solutions and implementations for the [Introduction to LangChain](https://academy.langchain.com/courses/foundation-introduction-to-langchain-python) course provided by LangChain Academy.

## Projects Included 📁

* **Personal Chef** – An AI assistant focused on culinary creativity and recipe management.
* **Wedding Planner** – A specialized chain for organizing events and logistical planning.
* **Email Assistant** – An automated agent designed to draft and categorize professional communications.
* **Agent-chat-ui** - A modern web interface powered by `agentchat.vercel.ai` that provides a graphical environment (GUI) to interact with the **Email Assistant**

## 🛠 Prerequisites

* **Python:** `>=3.12, <3.14`
* **Package Manager:** [uv](https://docs.astral.sh/uv/)

## 🚀 Getting Started

To get this project running locally, follow these steps:

### 1. Environment Configuration
The project requires several environment variables (such as API keys) to function correctly. 

1. Locate the `.env.example` file in the root directory.
2. Create a copy of this file and rename it to `.env`.
3. Open the new `.env` file and insert your respective API keys.


### 2. Virtual Environment & Dependencies
To create a virtual environment and install all necessary packages, run:

```bash
uv sync
