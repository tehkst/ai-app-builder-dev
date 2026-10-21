"""Check for AI cost tracking and model tiers (step 5a): usage in every provider's shape, the price
maths (cached input, unpriced models never guessed), the pricing file itself, the loop and employee
runner totals (including the nudge re-run), and a full client mission that records usage per
employee and routes the light-tier Technical Writer to the provider's smaller model."""
from __future__ import annotations

import os
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import List, Tuple
from unittest import mock

import yaml

from app.platform.ai_costs import PRICING_FILE, add_usage, cost_of, model_for_tier, normalize, summarize
from app.platform.clients import work
from app.platform.nautilus.loop import AgentLoop
from app.platform.nautilus.loop_check import turn
from app.platform.nautilus.tools import ToolRegistry
from app.platform.orca import MissionStore, Orca, load_workforce
from app.platform.orca.employee_runner import run_employee
from app.platform.orca.orca_check import PASS, Pod, finish, write
from app.platform.orca.specialists_check import HANDOVER
from app.platform.runtime.provider_router import SUPPORTED_MODELS

OPENAI_USAGE = {"input_tokens": 1_000_000, "input_tokens_details": {"cached_tokens": 200_000}, "output_tokens": 100_000}
DEEPSEEK_USAGE = {"prompt_tokens": 2_000, "prompt_cache_hit_tokens": 500, "completion_tokens": 300}


def with_usage(chat_turn, provider: str = "openai", model: str = "gpt-5.5", usage=None):
    return replace(chat_turn, provider=provider, model=model, usage=usage or {"input_tokens": 1000, "output_tokens": 100})


def check_maths() -> None:
    assert normalize(OPENAI_USAGE) == {"input": 1_000_000, "cached": 200_000, "output": 100_000}
    assert normalize(DEEPSEEK_USAGE) == {"input": 2_000, "cached": 500, "output": 300}
    assert normalize({}) == {"input": 0, "cached": 0, "output": 0}
    assert cost_of("openai", "gpt-5.5", normalize(OPENAI_USAGE)) == 7.1, "800k x $5 + 200k x $0.50 + 100k x $30"
    flash = cost_of("deepseek", "deepseek-v4-flash", normalize(DEEPSEEK_USAGE))
    assert flash == round((2_000 * 0.30 + 300 * 1.20) / 1e6, 6), "no cached price listed: cached input at the input rate"
    assert cost_of("openai", "gpt-5.5-mini", {"input": 10, "output": 10}) is None, "no price set: never guessed"
    total = {}
    add_usage(total, "openai", "gpt-5.5", OPENAI_USAGE)
    add_usage(total, "openai", "gpt-5.5", OPENAI_USAGE)
    assert total == {"provider": "openai", "model": "gpt-5.5", "calls": 2, "input": 2_000_000, "cached": 400_000, "output": 200_000}
    summary = summarize([{"employee": "builder", **total}, {"employee": "technical_writer", "provider": "openai",
                                                            "model": "gpt-5.5-mini", "calls": 1, "input": 50, "output": 5}])
    assert summary["cost_usd"] == 14.2 and summary["unpriced"] == ["openai/gpt-5.5-mini"] and summary["calls"] == 3
    assert summary["by_employee"]["builder"]["cost_usd"] == 14.2 and summary["by_employee"]["technical_writer"]["cost_usd"] == 0
    assert summarize([])["tokens"] == 0
    assert model_for_tier("openai", "gpt-5.5", "light") == "gpt-5.5", "no verified light model listed: standard"
    assert model_for_tier("deepseek", "deepseek-v4-pro", "light") == "deepseek-v4-pro"
    assert model_for_tier("openai", "gpt-5.5", "strong") == "gpt-5.5", "unlisted tier: the standard model"
    assert model_for_tier("openai", "gpt-5.5", "standard") == "gpt-5.5"


def check_pricing_file() -> None:
    config = yaml.safe_load(PRICING_FILE.read_text())
    for provider, models in (config.get("prices") or {}).items():
        assert provider in SUPPORTED_MODELS, provider
        for model, price in models.items():
            assert model in SUPPORTED_MODELS[provider], f"{provider}/{model} isn't a supported model"
            assert {"input", "output"} <= set(price) and all(isinstance(v, (int, float)) and v >= 0 for v in price.values()), price
    for provider, tiers in (config.get("tiers") or {}).items():
        for tier, model in tiers.items():
            assert tier in ("light", "strong") and model in SUPPORTED_MODELS[provider], (provider, tier, model)
    team = load_workforce()
    assert team.get("technical_writer").model_tier == "light"
    assert all(e.model_tier == "standard" for e in team.employees.values() if e.employee_id != "technical_writer")


def check_loop_and_runner(base: Path) -> None:
    replies = iter([with_usage(turn("thinking")), with_usage(turn("done"))])
    loop = AgentLoop(chat=lambda m, t: next(replies), tools=ToolRegistry([]), workspace_root=str(base), system_prompt="test")
    run = loop.run("go")
    run = loop.resume(run.messages)
    assert run.usage == {"openai/gpt-5.5": {"provider": "openai", "model": "gpt-5.5", "calls": 1, "input": 1000,
                                             "cached": 0, "output": 100}}, run.usage
    # The runner nudges an employee that forgot final_output: both runs count.
    builder = load_workforce().get("builder")
    script = iter([with_usage(turn("I wrote it."))] + [with_usage(t) for t in finish("f", {"summary": "s", "files_changed": []})])
    sink: List[dict] = []
    result = run_employee(builder, assignment="do it", workspace_root=str(base), chat=lambda m, t: next(script),
                          output_schema={"type": "object"}, allow_writes=False, allow_execution=False, usage_sink=sink)
    assert result.output is not None and sink == [{"employee": "builder", "provider": "openai", "model": "gpt-5.5",
                                                   "calls": 3, "input": 3000, "cached": 0, "output": 300}], sink


class PricedPod(Pod):
    """The scripted pod, answering as the model it was built for (so usage carries that model)."""

    def __init__(self, scripts, built: List[Tuple[str, str]]) -> None:
        super().__init__(scripts)
        self.built = built

    def as_model(self, provider: str, model: str):
        self.built.append((provider, model))
        return lambda messages, tools: with_usage(self(messages, tools), provider, model)


def tiered_pricing(base: Path) -> Path:
    """A pricing file that lists a light model, as the founder would after verifying one."""
    path = base / "ai-pricing.yaml"
    config = yaml.safe_load(PRICING_FILE.read_text())
    config["tiers"] = {"openai": {"light": "gpt-5.5-mini"}}
    path.write_text(yaml.safe_dump(config))
    return path


def check_mission_costs(base: Path) -> None:
    os.environ["ASF_CLIENT_WORKSPACES"] = str(base / "ws")
    source = base / "shop"
    source.mkdir()
    (source / "a.txt").write_text("old\n")
    copy = work.prepare_copy(str(source), "CL-cost")
    plan = {"summary": "s", "tasks": [{"title": "Fix", "description": "d", "specialty": "general", "files": ["a.txt"],
                                       "acceptance_checks": ["grep -q done a.txt"]}]}
    built: List[Tuple[str, str]] = []
    pod = PricedPod({"Software Architect": [*finish("p", plan)], "Builder": [*write("b", "a.txt", "done\n", "ok")],
                     "QA Lead": [*finish("q", PASS)], "Security Reviewer": [*finish("s", PASS)],
                     "Technical Writer": [*finish("w", HANDOVER)]}, built)
    orca = Orca(store=MissionStore(base / "missions"))  # no injected chat: the real model selection runs
    mission = orca.start_mission("Fix it", copy["workspace"], client={"client_id": "CL-cost", "client_name": "Shop"},
                                 client_base=work.work_root() / "CL-cost" / "work", ai=("openai", "gpt-5.5"),
                                 baseline_dir=copy["git_dir"])
    from app.platform.ai_costs import service as costs

    with mock.patch("app.platform.nautilus.chat_providers.build_chat_fn", pod.as_model), \
            mock.patch.object(costs, "PRICING_FILE", tiered_pricing(base)):
        orca.run(mission.mission_id)
        orca.decide_execution(mission.mission_id, approved=False)
        mission = orca.run(mission.mission_id)
    assert mission.status == "complete_unverified", (mission.status, mission.events[-2:])
    assert set(built) == {("openai", "gpt-5.5")}, f"client work stays on the agreed model, tiers or not: {built}"
    by_employee = {u["employee"]: u["model"] for u in mission.usage}
    assert by_employee == {"architect": "gpt-5.5", "builder": "gpt-5.5", "qa_lead": "gpt-5.5",
                           "security_reviewer": "gpt-5.5", "technical_writer": "gpt-5.5"}, by_employee
    cost = summarize(mission.usage)
    assert cost["unpriced"] == [] and cost["cost_usd"] > 0, cost
    assert set(cost["by_employee"]) == set(by_employee)
    reloaded = MissionStore(base / "missions").load(mission.mission_id)
    assert reloaded.usage == mission.usage, "usage survives a restart"

    # Platform (generated-app) missions do follow tiers: a docs task goes to the light model.
    apps = base / "apps"
    (apps / "demo").mkdir(parents=True)
    docs = {"summary": "s", "tasks": [{"title": "Docs", "description": "d", "specialty": "docs", "files": ["README.md"],
                                       "acceptance_checks": ["grep -q Shop README.md"]}]}
    built.clear()
    pod = PricedPod({"Software Architect": [*finish("p", docs)], "Technical Writer": [*write("w", "README.md", "# Shop\n", "ok")],
                     "QA Lead": [*finish("q", PASS)]}, built)
    orca = Orca(store=MissionStore(base / "app-missions"), sandbox_base=apps)
    platform = orca.start_mission("Write docs", str(apps / "demo"))
    with mock.patch("app.platform.nautilus.chat_providers.build_chat_fn", pod.as_model), \
            mock.patch.object(costs, "PRICING_FILE", tiered_pricing(base)), \
            mock.patch("app.platform.runtime.provider_router.selected_provider", lambda value=None: "openai"), \
            mock.patch("app.platform.runtime.provider_router.default_model", lambda provider=None: "gpt-5.5"), \
            mock.patch.object(Orca, "chat", property(lambda self: pod.as_model("openai", "gpt-5.5"))):
        orca.run(platform.mission_id)
        orca.decide_execution(platform.mission_id, approved=False)
        platform = orca.run(platform.mission_id)
    assert platform.status == "complete_unverified", platform.status
    models = {u["employee"]: u["model"] for u in platform.usage}
    assert models == {"architect": "gpt-5.5", "technical_writer": "gpt-5.5-mini", "qa_lead": "gpt-5.5"}, models


def main() -> None:
    check_maths()
    check_pricing_file()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        check_loop_and_runner(base)
        check_mission_costs(base)
    print("AI COSTS CHECK PASSED")


if __name__ == "__main__":
    main()
