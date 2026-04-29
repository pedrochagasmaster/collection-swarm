"""YAML configuration loading for Collection Swarm."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from collection_swarm.models import ModelConfig, Profile, SimulationSettings, Strategy


DEFAULT_CONFIG_DIR = Path("config")


class AppConfig(BaseModel):
    profiles: dict[str, Profile]
    strategies: dict[str, Strategy]
    models: dict[str, ModelConfig]
    simulation: SimulationSettings = Field(default_factory=SimulationSettings)

    def profile(self, profile_id: str) -> Profile:
        try:
            return self.profiles[profile_id]
        except KeyError as exc:
            raise KeyError(f"unknown profile '{profile_id}'") from exc

    def strategy(self, strategy_id: str) -> Strategy:
        try:
            return self.strategies[strategy_id]
        except KeyError as exc:
            raise KeyError(f"unknown strategy '{strategy_id}'") from exc

    def model(self, model_id: str) -> ModelConfig:
        try:
            return self.models[model_id]
        except KeyError as exc:
            raise KeyError(f"unknown model '{model_id}'") from exc

    @property
    def default_conversation_model(self) -> str:
        for model in self.models.values():
            if model.backend == "scripted":
                return model.id
        return next(iter(self.models))

    @property
    def default_judge_model(self) -> str:
        for model in self.models.values():
            if model.backend in {"heuristic", "scripted"}:
                return model.id
        return next(iter(self.models))


def load_yaml(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def _items_by_id(raw: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(raw, dict) and key in raw:
        raw = raw[key]
    if isinstance(raw, dict):
        return [dict(value, id=item_id) if isinstance(value, dict) and "id" not in value else value for item_id, value in raw.items()]
    if isinstance(raw, list):
        return raw
    raise ValueError(f"expected {key} to be a list or mapping")


def load_profiles(path: Path) -> dict[str, Profile]:
    profiles = [Profile.model_validate(item) for item in _items_by_id(load_yaml(path), "profiles")]
    return {profile.id: profile for profile in profiles}


def load_strategies(path: Path) -> dict[str, Strategy]:
    strategies = [Strategy.model_validate(item) for item in _items_by_id(load_yaml(path), "strategies")]
    return {strategy.id: strategy for strategy in strategies}


def load_models(path: Path) -> dict[str, ModelConfig]:
    raw = load_yaml(path)
    models: list[ModelConfig] = []
    tiers = raw.get("tiers", {}) if isinstance(raw, dict) else {}
    if tiers:
        for tier in tiers.values():
            for model_data in tier.get("models", []):
                models.append(ModelConfig.model_validate(model_data))
    else:
        models = [ModelConfig.model_validate(item) for item in _items_by_id(raw, "models")]
    if not models:
        raise ValueError("at least one model must be configured")
    return {model.id: model for model in models}


def load_simulation_settings(path: Path) -> SimulationSettings:
    raw = load_yaml(path)
    conversation = raw.get("conversation", {})
    stalemate = conversation.get("stalemate", {})
    normalized = {
        "conversation": {
            "max_turns": conversation.get("max_turns", 20),
            "end_signal": conversation.get("end_signal", "[END_CONVERSATION]"),
            "stalemate_window": stalemate.get("window", conversation.get("stalemate_window", 3)),
            "stalemate_similarity_threshold": stalemate.get(
                "similarity_threshold", conversation.get("stalemate_similarity_threshold", 0.6)
            ),
        },
        "default_repetitions": raw.get("matrix", {}).get("default_repetitions", raw.get("default_repetitions", 1)),
        "min_compliance_score": raw.get("compliance", {}).get("min_compliance_score", 0.8),
        "max_escalation_risk": raw.get("compliance", {}).get("max_escalation_risk", 0.3),
        "objection_taxonomy": raw.get("objection_taxonomy", []),
    }
    return SimulationSettings.model_validate(normalized)


def load_app_config(config_dir: Path | str = DEFAULT_CONFIG_DIR) -> AppConfig:
    base = Path(config_dir)
    return AppConfig(
        profiles=load_profiles(base / "debtor_profiles.yaml"),
        strategies=load_strategies(base / "collector_strategies.yaml"),
        models=load_models(base / "models.yaml"),
        simulation=load_simulation_settings(base / "simulation.yaml"),
    )
