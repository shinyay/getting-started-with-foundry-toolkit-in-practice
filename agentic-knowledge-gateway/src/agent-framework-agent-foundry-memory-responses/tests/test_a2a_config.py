import unittest

from gateway.a2a_config import (
    a2a_base_url,
    agent_card_url,
    build_agent_card,
    build_agent_endpoint,
    has_v1_jsonrpc_interface,
)


class A2AConfigTests(unittest.TestCase):
    def test_card_declares_v1_and_tutorial_skill(self) -> None:
        card = build_agent_card().as_dict()
        self.assertEqual(card["version"], "1.0")
        self.assertEqual(
            card["skills"][0]["id"], "tutorial-knowledge-memory"
        )
        self.assertIn("shared tutorial scope", card["description"])

    def test_endpoint_enables_responses_and_a2a(self) -> None:
        endpoint = build_agent_endpoint().as_dict()
        protocols = endpoint["protocol_configuration"]
        self.assertEqual(protocols["responses"], {})
        self.assertEqual(protocols["a2a"], {})

    def test_urls_target_explicit_v1_card(self) -> None:
        endpoint = "https://example.test/api/projects/demo/"
        agent = "agentic knowledge gateway"
        self.assertEqual(
            a2a_base_url(endpoint, agent),
            "https://example.test/api/projects/demo/agents/"
            "agentic%20knowledge%20gateway/endpoint/protocols/a2a",
        )
        self.assertTrue(
            agent_card_url(endpoint, agent).endswith(
                "/agentCard/v1.0"
            )
        )

    def test_served_card_requires_v1_jsonrpc_interface(self) -> None:
        self.assertTrue(
            has_v1_jsonrpc_interface(
                {
                    "supportedInterfaces": [
                        {
                            "protocolBinding": "JSONRPC",
                            "protocolVersion": "1.0",
                        }
                    ]
                }
            )
        )
        self.assertFalse(
            has_v1_jsonrpc_interface(
                {
                    "supportedInterfaces": [
                        {
                            "protocolBinding": "JSONRPC",
                            "protocolVersion": "0.3",
                        }
                    ]
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
