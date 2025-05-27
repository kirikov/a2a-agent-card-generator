# a2a-agent-card-generator
A Python tool that analyzes an agent’s source code and automatically generates an A2A (Agent-to-Agent) metadata card.

This app parses a multi-file Python codebase to extract agent capabilities, input/output formats, tool usage, and behavior patterns. It then produces a structured A2A card (in JSON or Markdown) that documents the agent’s interface and purpose—ready to be shared or integrated in agent ecosystems.

# Getting started

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the app

python metadata.py

# Format of the A2A card

Application will download the agent from NEAR AI Hub, traverse files starting from agent.py 
and use OpenAI LLM to generate A2A Agent Card according to standard.
