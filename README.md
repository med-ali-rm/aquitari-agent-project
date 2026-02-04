# Aquitari Vital Agent

This project is being built for Commit To Change: An AI Agents Hackathon.  
It is still a work in progress and will be updated until completion.

---

## ⚠️ Important Note

The agent is being developed with n8n and will also integrate with Opik for observability (additional Opik integrations will be documented once finalized).  
**New day is a fresh page** → conversations do not carry over from yesterday to today.  
The workflows will be added to the project folder once finished.  
Since the app uses a **Large Language Model (LLM)**, you should **not enter personal details** — I cannot control or delete what the LLM itself may generate or retain internally.  

⚠️ **Note:** Aquitari provides wellness guidance and is not a substitute for professional medical or financial advice.  
Since the app uses a Large Language Model (LLM), you should not enter personal details — I cannot control or delete what the LLM itself may generate or retain internally.

---

## 🪪 Identity

- **App Name**: Aquitari Vital Agent  
- **AI Agent**: Vital (Aquitari Agent)

---

## ⚠️ Disclaimer

**Note:** Aquitari provides wellness guidance and is not a substitute for professional medical or financial advice.  
All outputs (Zen commands, budget tips, resilience prompts) are wellness guidance only — not medical or financial prescriptions.

---

## 📜 License

This project is licensed under the MIT License.  
See the LICENSE file for details.  

All code is released under the MIT License, ensuring openness and flexibility for future development.  
Shared under the MIT License to inspire collaboration and growth.

---

## 🚧 Development Status

This project is fully functional and ready for submission to the Commit To Change Hackathon.  
At the same time, it remains under active development: future iterations will expand the knowledge graph, refine workflows, and add integrations.  

Scripts require certain environment variables (e.g. Redis, `.env` configuration) to run correctly.  
The knowledge graph JSON file included in `brain-api/data` is a starting point and will continue to evolve as the agent grows.  

⚠️ **Reminder:** Aquitari provides wellness guidance and is not a substitute for professional medical or financial advice.


---

## 🚀 Quick Start Guide

Follow these steps to set up and run the Aquitari Vita Agent:

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd aquitari-vita-agent

2. **Install requirements**

pip install -r requirements.txt

3. **Install Redis**
- Make sure Redis is installed and running locally:

redis-server

- Default connection: localhost:6379, db=0.


4. **Import n8n workflows**

- Import workflows
  - Open your n8n instance.  
  - Import the two workflow JSON files provided in the `workflows/` folder.  

- Set LLM credentials
  - Configure the API key or credentials for your chosen LLM.
    
-Set Redis credentials

- Publish workflows 
  - Make sure they are active.  

- Configure webhook URLs
  - Copy the **production webhook URL** for each of the two workflows.  
  - Paste these URLs into the `.env` file under the appropriate variables.  

-Enable Opik Observability
   -configure Opik with your n8n instance.  


5. **Modify environment variables**

-Rename the file:
   - Change the name of `.env.example` → `.env`

- Update the values for:
   - REDIS_HOST, REDIS_PORT, REDIS_DB
   - N8N_WEBHOOK_URL
   - OPIK_API_KEY


6. **Run the agent**

- Start your n8n instance.
- Ensure the workflows are active and connected to Redis + Opik.
- Alternatively, you can run all services at once with:

python run_all_services.py

⚠️ **Note:** If you face issues running `run_all_services.py` (for example, port conflicts or missing file errors), you can start the services one by one in this order:

1. `python main.py`
2. `python app.py`
3. `python app_scripts/redis_feedback_graph_updater.py`

This ensures each component runs correctly without overlapping processes.


⚠️ Reminder: Aquitari provides wellness guidance and is not a substitute for professional medical or financial advice.

📜 License: This project is MIT‑licensed — use at your own risk, as per MIT terms

---

## 🧠 Adaptive Knowledge Graph

The Aquitari Vital Agent uses a dynamic knowledge graph to link causes, exacerbates, and protective factors.  
- New risks and interventions are automatically added to the graph.  
- Relationships evolve over time based on user input and detected patterns.  
- This ensures the agent’s guidance improves continuously, adapting to changing stress and spending behaviors.
- You can **visualize the knowledge graph** by running the script:

python visualize_your_knowledge_graph.py

---

## 🔗 Workflow Orchestration (n8n)

The Aquitari Vital Agent is fully orchestrated inside **n8n**.  
- All agent logic, state management, and workflow automation are implemented as n8n workflows.  
- Python scripts in `app_scripts/` provide supporting functions (e.g., knowledge graph updates, auto‑linking).  
- n8n handles incoming webhook events, routes data between the agent, Redis, and external services, and integrates with **Opik** for observability.  

This design makes the agent modular, transparent, and easy to extend with new integrations.

---

## 📊 Observability (Opik)

Opik is integrated directly into the n8n workflows to track the agent’s activity:  
- Captures **user inputs** as they enter the system.  
- Logs **agent outputs** for monitoring and evaluation.  
- Provides visibility into how the agent processes data and delivers guidance.  

In the code, Opik is used specifically to track just the **input** and the **output** of the agent.  
This gives a clear vision of these two parameters, ensuring transparency and making it easier to evaluate and refine the agent’s behavior over time.

---

## 🙏 Acknowledgments

Special thanks to the Commit To Change Hackathon organizers and community for this opportunity.  
I am happy to have participated in this challenge — it was my first hackathon, and I’m grateful to be a player, to learn, and to grow through the experience.  

Thanks also to **n8n** and **Opik**, which provided the backbone for workflow orchestration and observability in this project.  


⚠️ **Final Note:** Aquitari Vita Agent is designed to guide wellness and resilience, but it is not a substitute for professional medical or financial advice.  
Shared under the MIT License to encourage learning, collaboration, and future growth.
