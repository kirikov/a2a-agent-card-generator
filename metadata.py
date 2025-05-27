import json
import logging
import os
import tree_sitter_python as tspython
from pathlib import Path
from traceback import format_exc
from typing import List, Optional
from openai import OpenAI
from nearai import EntryLocation
from nearai.openapi_client import EntryInformation
from pydantic import BaseModel, HttpUrl
from nearai.registry import registry
from dotenv import load_dotenv
from tree_sitter import Language, Parser

from crawler import get_concatenated_files_to_analyze

load_dotenv(verbose=True)
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


class Provider(BaseModel):
    organization: str
    url: HttpUrl


class Capabilities(BaseModel):
    streaming: Optional[bool] = None
    pushNotifications: Optional[bool] = None
    stateTransitionHistory: Optional[bool] = None


class Authentication(BaseModel):
    schemes: List[str]
    credentials: Optional[str] = None


class Skill(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str]
    examples: Optional[List[str]] = None
    inputModes: Optional[List[str]] = None
    outputModes: Optional[List[str]] = None


class AgentCard(BaseModel):
    name: str
    description: str
    url: HttpUrl
    provider: Optional[Provider] = None
    version: str
    documentationUrl: Optional[HttpUrl] = None
    capabilities: Capabilities
    authentication: Authentication
    defaultInputModes: List[str]
    defaultOutputModes: List[str]
    skills: List[Skill]


def index(entry: EntryInformation):
    entry_location = EntryLocation(
        namespace=entry.namespace,
        name=entry.name,
        version=entry.version
    )
    entry_location_str = f"{entry.namespace}/{entry.name}/{entry.version}"
    logging.info(f"Starting indexing of entry: {entry_location_str}")

    # Download agent codebase
    path = registry.download(entry_location, show_progress=True, verbose=True, force=True)
    logging.info(f"Entry was downloaded to {path}")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # agent_py = Path(path, "agent.py").read_text("utf-8")
    agent_py = get_concatenated_files_to_analyze("agent.py", path)

    # have fixed context window
    if len(agent_py) >= 100000:
        agent_py = agent_py[:100000]

    metadata_json = Path(path, "metadata.json").read_text("utf-8")

    logging.info(f"Requesting LLM to generate Agent Card.")
    resp = client.responses.create(
        instructions="You're very good python engineer, and you can understand the python code very well."
                     "You're provided with the python code that is a entrypoint to the agent (agent.py).  "
                     "You're provided with the current description of the agent that can be incomplete (metadata.json)."
                     "Your task is to generate very detailed description on what this agent is doing "
                     "and return it in the format of agent card with given schema:"
                     f"{json.dumps(AgentCard.model_json_schema(), indent=2)}"
                     f"For the provided use: near.ai"
                     f"For the provider url use: near.ai"
                     f"For the agent url use: https://app.near.ai/agents/{entry_location_str}",
        input=[
            {"role": "user", "content": f"// agent.py\n```python\n{agent_py}\n```"},
            {"role": "user", "content": f"// metadata.json\n```json\n{metadata_json}\n```"},
        ],
        model="o4-mini",
    )

    card_raw = resp.output[1].content[0].text
    logging.info(f"Agent card for {entry_location_str} created.")

    Path('./cards').mkdir(exist_ok=True)
    card_file_path = Path("./cards", f"{entry_location_str.replace('/', '_')}.json")

    try:
        if "```json" in card_raw:
            card_raw = card_raw.split("```json")[1].split("```")[0]

        card = AgentCard(**json.loads(card_raw))
        with open(card_file_path, "w", encoding="utf-8") as f:
            f.write(card.model_dump_json(indent=2))
        logging.info(f"Agent card for {entry_location_str} was successfully saved to {card_file_path}.")
    except Exception as e:
        logging.error(f"Error parsing agent card {card_raw}.\nError: {format_exc()}")
        with open(card_file_path, "w", encoding="utf-8") as f:
            f.write(card_raw)


def get_agents():
    logging.info("Downloading entries from NEAR AI registry")
    has_more = True
    entries: List[EntryInformation] = []
    offset = 0
    while has_more:
        agents = registry.list(
            namespace="",
            category="agent",
            tags="",
            total=1000,
            offset=offset,
            show_all=True,
            show_latest_version=True
        )
        entries.extend(agents)
        if len(agents) < 1000:
            has_more = False
        else:
            offset += len(agents)

    entries = sorted(entries, key=lambda entry: entry.num_stars, reverse=True)

    logging.info(f"Downloaded {len(entries)} entries")
    return entries


def main():
    entries = get_agents()

    # For testing
    entries = entries[1:10]
    for entry in entries:
        index(entry)


if __name__ == "__main__":
    main()