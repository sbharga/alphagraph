from pathlib import Path

from alphagraph.llm.provider import (
    ProviderKind,
    build_agent_routes_from_env,
    build_default_agent_suite,
)


def test_build_agent_routes_defaults_to_hackathon_stack() -> None:
    routes = build_agent_routes_from_env({})

    assert routes.hypothesis.provider == ProviderKind.GOOGLE
    assert routes.hypothesis.model == "gemini-2.5-flash"
    assert routes.hypothesis.api_key_env == "GOOGLE_API_KEY"

    assert routes.coding.provider == ProviderKind.ANTHROPIC
    assert routes.coding.model == "claude-sonnet-4-20250514"
    assert routes.coding.api_key_env == "ANTHROPIC_API_KEY"

    assert routes.critic.provider == ProviderKind.DEEPSEEK
    assert routes.critic.model == "deepseek-reasoner"
    assert routes.critic.api_key_env == "DEEPSEEK_API_KEY"


def test_build_agent_routes_normalizes_common_model_aliases() -> None:
    routes = build_agent_routes_from_env(
        {
            "HYPOTHESIS_MODEL": "gemini-pro",
            "CODING_MODEL": "sonnet-4.6",
            "CRITIC_MODEL": "deepseek-v3.2",
        }
    )

    assert routes.hypothesis.model == "gemini-2.5-pro"
    assert routes.coding.model == "claude-sonnet-4-20250514"
    assert routes.critic.model == "deepseek-reasoner"


def test_build_default_agent_suite_uses_role_specific_providers_when_keys_present(
    monkeypatch,
) -> None:
    prompt_dir = (
        Path(__file__).resolve().parents[1] / "src" / "alphagraph" / "prompts"
    )
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")

    suite = build_default_agent_suite(prompt_dir)

    assert suite.hypothesis_agent.provider.primary is not None
    assert suite.hypothesis_agent.provider.primary.provider_name == ProviderKind.GOOGLE
    assert suite.hypothesis_agent.provider.primary.model == "gemini-2.5-flash"

    assert suite.coding_agent.provider.primary is not None
    assert suite.coding_agent.provider.primary.provider_name == ProviderKind.ANTHROPIC
    assert suite.coding_agent.provider.primary.model == "claude-sonnet-4-20250514"

    assert suite.factor_critic.provider.primary is not None
    assert suite.factor_critic.provider.primary.provider_name == ProviderKind.DEEPSEEK
    assert suite.factor_critic.provider.primary.model == "deepseek-reasoner"


def test_build_default_agent_suite_falls_back_to_demo_per_role_when_keys_missing(
    monkeypatch,
) -> None:
    prompt_dir = (
        Path(__file__).resolve().parents[1] / "src" / "alphagraph" / "prompts"
    )
    for key in [
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)

    suite = build_default_agent_suite(prompt_dir)

    assert suite.hypothesis_agent.provider.primary is None
    assert suite.coding_agent.provider.primary is None
    assert suite.factor_critic.provider.primary is None
