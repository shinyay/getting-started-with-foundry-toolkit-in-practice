#!/usr/bin/env python3
"""Write deterministic fictional knowledge directly into Foundry Memory."""

from __future__ import annotations

import asyncio
import sys

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import MemoryItemKind
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

from gateway.settings import GatewaySettings

FACTS = [
    "Project Shinya は、2027年に稼働予定の受注管理システム刷新プロジェクトの"
    "社内コードネームです。",
    "Project Shinya では、注文IDに UUID v4 ではなく ULID を採用しました。"
    "理由は、インデックスの局所性が高く、書き込みスループットが安定するため"
    "です。",
    "Project Shinya の本番デプロイ枠は、毎週火曜日の 02:00 から 04:00 JST "
    "です。この時間帯以外の本番反映は原則として行いません。",
    "Project Shinya のステージング環境の通称は harbor です。"
    "本番環境は lighthouse と呼びます。",
    "Project Shinya のオンコール引き継ぎミーティングは、毎週木曜日の "
    "10:00 JST に実施します。",
    "Project Shinya の ADR-014 では、イベントソーシングを採用しないことを"
    "決定しました。理由は、運用チームの学習コストと監査要件のバランスが"
    "見合わなかったためです。",
    "Project Shinya のリリース判定会議には、開発リード、QAリード、"
    "運用担当の3名の承認が必要です。",
]


async def seed() -> int:
    settings = GatewaySettings.from_env()
    async with (
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=settings.project_endpoint,
            credential=credential,
            allow_preview=True,
        ) as project,
    ):
        for fact in FACTS:
            item = await project.beta.memory_stores.create_memory(
                name=settings.memory_store_name,
                scope=settings.memory_scope,
                content=fact,
                kind=MemoryItemKind.USER_PROFILE,
            )
            if item.content != fact:
                print("service did not preserve the fact verbatim")
                return 1
            print(f"stored: {fact[:48]}...")

    print(f"\nseeded {len(FACTS)} deterministic facts")
    return 0


def main() -> int:
    load_dotenv(override=False)
    return asyncio.run(seed())


if __name__ == "__main__":
    sys.exit(main())
