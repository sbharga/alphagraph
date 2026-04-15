from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openai import OpenAI

from alphagraph.runtime.backtest_engine import evaluate_execution
from alphagraph.schemas import (
    CodegenOutput,
    CriticOutput,
    Critique,
    EvaluationResult,
    ExecutionResult,
    FactorSpec,
    GeneratedCode,
    HypothesisOutput,
)


class LLMProvider(Protocol):
    def generate_factor(
        self,
        *,
        brief: str,
        attempt_number: int,
        critique: Critique | None,
    ) -> FactorSpec: ...

    def generate_code(
        self,
        *,
        factor_spec: FactorSpec,
        attempt_number: int,
    ) -> GeneratedCode: ...

    def generate_critique(
        self,
        *,
        factor_spec: FactorSpec,
        evaluation: EvaluationResult,
        attempt_number: int,
    ) -> Critique: ...


class HypothesisAgent(Protocol):
    def propose(
        self,
        *,
        brief: str,
        attempt_number: int,
        prior_critique: Critique | None,
    ) -> HypothesisOutput: ...


class CodingAgent(Protocol):
    def translate(
        self,
        *,
        hypothesis: HypothesisOutput,
        attempt_number: int,
    ) -> CodegenOutput: ...


class FactorCriticAgent(Protocol):
    def review(
        self,
        *,
        hypothesis: HypothesisOutput,
        execution_result: ExecutionResult,
        attempt_number: int,
    ) -> CriticOutput: ...


@dataclass(frozen=True)
class AgentSuite:
    hypothesis_agent: HypothesisAgent
    coding_agent: CodingAgent
    factor_critic: FactorCriticAgent


class DemoLLMProvider:
    def generate_factor(
        self,
        *,
        brief: str,
        attempt_number: int,
        critique: Critique | None,
    ) -> FactorSpec:
        if attempt_number == 1:
            return FactorSpec(
                name="Cross-Sectional Price Level",
                thesis="Higher-priced stocks might keep outperforming in the very short term.",
                expression="rank(close)",
            )
        return FactorSpec(
            name="Five-Day Momentum",
            thesis="Recent winners should continue outperforming over the next day.",
            expression="rank(ts_return(close, 5))",
        )

    def generate_code(
        self,
        *,
        factor_spec: FactorSpec,
        attempt_number: int,
    ) -> GeneratedCode:
        return GeneratedCode(
            commentary=(
                "Generated a minimal backtest script that runs the factor through "
                "the fixed AlphaGraph harness."
            ),
            script=_script_template(factor_spec.expression),
        )

    def generate_critique(
        self,
        *,
        factor_spec: FactorSpec,
        evaluation: EvaluationResult,
        attempt_number: int,
    ) -> Critique:
        if "raw_price_level" in evaluation.reasons:
            return Critique(
                summary="The factor failed because it ranks stocks by raw price level.",
                root_cause="Raw prices are not stationary and are not comparable across securities.",
                revision_instructions=(
                    "Replace the raw price level with a stationary return-based signal, "
                    "preferably short-term momentum."
                ),
            )
        if evaluation.needs_revision:
            return Critique(
                summary="The factor is too weak for the demo thresholds.",
                root_cause="Sharpe or trade count missed the deterministic acceptance gates.",
                revision_instructions="Increase signal quality while staying inside the tiny DSL.",
            )
        return Critique(
            summary="The revised factor cleared the demo gates.",
            root_cause="The factor is now methodologically sound and strong enough for the demo.",
            revision_instructions="Present the result to a human reviewer before finalizing.",
        )


class OpenAILLMProvider:
    def __init__(self, *, model: str, prompt_dir: Path) -> None:
        self.client = OpenAI()
        self.model = model
        self.prompt_dir = prompt_dir

    def generate_factor(
        self,
        *,
        brief: str,
        attempt_number: int,
        critique: Critique | None,
    ) -> FactorSpec:
        guidance = critique.revision_instructions if critique else "Seed a naive first factor."
        return self._parse(
            FactorSpec,
            "hypothesis.md",
            f"Brief:\n{brief}\n\nAttempt: {attempt_number}\n\nGuidance:\n{guidance}",
        )

    def generate_code(
        self,
        *,
        factor_spec: FactorSpec,
        attempt_number: int,
    ) -> GeneratedCode:
        return self._parse(
            GeneratedCode,
            "codegen.md",
            (
                "Write a runnable Python script for this factor.\n"
                f"Attempt: {attempt_number}\n"
                f"Factor JSON:\n{factor_spec.model_dump_json(indent=2)}"
            ),
        )

    def generate_critique(
        self,
        *,
        factor_spec: FactorSpec,
        evaluation: EvaluationResult,
        attempt_number: int,
    ) -> Critique:
        return self._parse(
            Critique,
            "critic.md",
            (
                f"Attempt: {attempt_number}\n"
                f"Factor JSON:\n{factor_spec.model_dump_json(indent=2)}\n\n"
                f"Evaluation JSON:\n{evaluation.model_dump_json(indent=2)}"
            ),
        )

    def _parse(self, schema: type, prompt_name: str, user_input: str):
        prompt = (self.prompt_dir / prompt_name).read_text()
        response = self.client.responses.parse(
            model=self.model,
            instructions=prompt,
            input=user_input,
            text_format=schema,
            temperature=0.2,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is not None:
            return parsed
        return schema.model_validate_json(response.output_text)


class ResilientLLMProvider:
    def __init__(
        self,
        *,
        primary: OpenAILLMProvider | None,
        fallback: DemoLLMProvider | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback or DemoLLMProvider()

    def generate_factor(
        self,
        *,
        brief: str,
        attempt_number: int,
        critique: Critique | None,
    ) -> FactorSpec:
        if self.primary is None:
            return self.fallback.generate_factor(
                brief=brief,
                attempt_number=attempt_number,
                critique=critique,
            )
        try:
            return self.primary.generate_factor(
                brief=brief,
                attempt_number=attempt_number,
                critique=critique,
            )
        except Exception:
            return self.fallback.generate_factor(
                brief=brief,
                attempt_number=attempt_number,
                critique=critique,
            )

    def generate_code(
        self,
        *,
        factor_spec: FactorSpec,
        attempt_number: int,
    ) -> GeneratedCode:
        if self.primary is None:
            return self.fallback.generate_code(
                factor_spec=factor_spec,
                attempt_number=attempt_number,
            )
        try:
            return self.primary.generate_code(
                factor_spec=factor_spec,
                attempt_number=attempt_number,
            )
        except Exception:
            return self.fallback.generate_code(
                factor_spec=factor_spec,
                attempt_number=attempt_number,
            )

    def generate_critique(
        self,
        *,
        factor_spec: FactorSpec,
        evaluation: EvaluationResult,
        attempt_number: int,
    ) -> Critique:
        if self.primary is None:
            return self.fallback.generate_critique(
                factor_spec=factor_spec,
                evaluation=evaluation,
                attempt_number=attempt_number,
            )
        try:
            return self.primary.generate_critique(
                factor_spec=factor_spec,
                evaluation=evaluation,
                attempt_number=attempt_number,
            )
        except Exception:
            return self.fallback.generate_critique(
                factor_spec=factor_spec,
                evaluation=evaluation,
                attempt_number=attempt_number,
            )


class ProviderBackedHypothesisAgent:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def propose(
        self,
        *,
        brief: str,
        attempt_number: int,
        prior_critique: Critique | None,
    ) -> HypothesisOutput:
        factor_spec = self.provider.generate_factor(
            brief=brief,
            attempt_number=attempt_number,
            critique=prior_critique,
        )
        return HypothesisOutput(factor_spec=factor_spec)


class ProviderBackedCodingAgent:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def translate(
        self,
        *,
        hypothesis: HypothesisOutput,
        attempt_number: int,
    ) -> CodegenOutput:
        generated_code = self.provider.generate_code(
            factor_spec=hypothesis.factor_spec,
            attempt_number=attempt_number,
        )
        return CodegenOutput(generated_code=generated_code)


class ProviderBackedFactorCritic:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def review(
        self,
        *,
        hypothesis: HypothesisOutput,
        execution_result: ExecutionResult,
        attempt_number: int,
    ) -> CriticOutput:
        evaluation = evaluate_execution(
            expression=hypothesis.factor_spec.expression,
            execution=execution_result,
        )
        critique = self.provider.generate_critique(
            factor_spec=hypothesis.factor_spec,
            evaluation=evaluation,
            attempt_number=attempt_number,
        )
        return CriticOutput(
            evaluation=evaluation,
            critique=critique,
            needs_revision=evaluation.needs_revision,
        )


def build_agent_suite(provider: LLMProvider) -> AgentSuite:
    return AgentSuite(
        hypothesis_agent=ProviderBackedHypothesisAgent(provider),
        coding_agent=ProviderBackedCodingAgent(provider),
        factor_critic=ProviderBackedFactorCritic(provider),
    )


def build_default_agent_suite(prompt_dir: Path) -> AgentSuite:
    import os

    api_key_present = bool(os.getenv("OPENAI_API_KEY"))
    openai_provider = (
        OpenAILLMProvider(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            prompt_dir=prompt_dir,
        )
        if api_key_present
        else None
    )
    return build_agent_suite(ResilientLLMProvider(primary=openai_provider))


def _script_template(expression: str) -> str:
    return f"""from pathlib import Path
import os

from alphagraph.runtime.backtest_engine import run_backtest_from_expression


dataset_path = Path(os.environ[\"ALPHAGRAPH_DATASET_PATH\"])
output_path = Path(os.environ[\"ALPHAGRAPH_OUTPUT_PATH\"])
result = run_backtest_from_expression(dataset_path, {expression!r})
output_path.write_text(result.model_dump_json(indent=2))
print(\"executed factor {expression}\")
"""
