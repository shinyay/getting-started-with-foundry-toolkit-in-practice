"""Run the Agentic Knowledge Gateway as a Responses Hosted Agent."""

import asyncio
import logging

from dotenv import load_dotenv

from gateway.app import run_gateway
from gateway.settings import GatewaySettings


def main() -> None:
    load_dotenv(override=False)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_gateway(GatewaySettings.from_env()))


if __name__ == "__main__":
    main()
