# Copyright (c) Microsoft. All rights reserved.

import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=False)


AGENT_INSTRUCTIONS = """
あなたは利用者の理解を助けるアシスタントです。回答は必ず次の順序で構成します。

1. まず、利用者が自分で答えにたどり着くための示唆を1つか2つ示します。考える
   切り口、着目すべき点、簡単な問いかけのいずれかを使い、この段階では答えそのもの
   を書きません。
2. 次に区切り線として --- だけの行を入れます。
3. その後に、質問に対する正確な答えを簡潔に示します。

日本語で回答し、不明なことは推測せず分からないと述べます。示唆の後には必ず答えを
提示し、出し惜しみはしません。
""".strip()


def main() -> None:
    model_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") or os.getenv("FOUNDRY_MODEL_NAME")
    if not model_name:
        raise RuntimeError(
            "Model deployment name is not configured. Set "
            "AZURE_AI_MODEL_DEPLOYMENT_NAME or FOUNDRY_MODEL_NAME."
        )

    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=model_name,
        credential=DefaultAzureCredential(),
    )

    agent = Agent(
        client=client,
        instructions=AGENT_INSTRUCTIONS,
        # History will be managed by the hosting infrastructure, thus there
        # is no need to store history by the service. Learn more at:
        # https://developers.openai.com/api/reference/resources/responses/methods/create
        default_options={"store": False},
    )

    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
