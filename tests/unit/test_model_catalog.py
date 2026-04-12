"""Unit tests for model catalog."""

from __future__ import annotations

from vaultbot.llm.catalog import ModelCapability, ModelCatalog, ModelInfo


def _make_model(model_id: str, provider: str = "test", **kwargs: object) -> ModelInfo:
    return ModelInfo(model_id=model_id, provider=provider, **kwargs)  # type: ignore[arg-type]


class TestModelCatalog:
    def test_register_and_resolve(self) -> None:
        cat = ModelCatalog()
        cat.register_model(_make_model("gpt-4o", "openai"))
        assert cat.resolve("gpt-4o") is not None
        assert cat.model_count == 1

    def test_resolve_missing(self) -> None:
        cat = ModelCatalog()
        assert cat.resolve("nope") is None

    def test_alias(self) -> None:
        cat = ModelCatalog()
        cat.register_model(_make_model("gpt-4o", "openai"))
        cat.register_alias("smart", "gpt-4o")
        assert cat.resolve("smart") is not None

    def test_search(self) -> None:
        cat = ModelCatalog()
        cat.register_model(_make_model("gpt-4o", "openai", display_name="GPT-4o"))
        cat.register_model(_make_model("claude-3", "anthropic", display_name="Claude 3"))
        results = cat.search("gpt")
        assert len(results) == 1

    def test_filter_by_capability(self) -> None:
        cat = ModelCatalog()
        cat.register_model(
            _make_model("gpt-4o", capabilities=[ModelCapability.VISION, ModelCapability.CHAT])
        )
        cat.register_model(_make_model("gpt-3.5", capabilities=[ModelCapability.CHAT]))
        vision = cat.filter_by_capability(ModelCapability.VISION)
        assert len(vision) == 1

    def test_filter_by_provider(self) -> None:
        cat = ModelCatalog()
        cat.register_model(_make_model("a", "openai"))
        cat.register_model(_make_model("b", "anthropic"))
        assert len(cat.filter_by_provider("openai")) == 1

    def test_list_all(self) -> None:
        cat = ModelCatalog()
        cat.register_model(_make_model("a"))
        cat.register_model(_make_model("b"))
        assert len(cat.list_all()) == 2

    def test_cheapest(self) -> None:
        cat = ModelCatalog()
        cat.register_model(_make_model("expensive", input_cost_per_1k=10.0))
        cat.register_model(_make_model("cheap", input_cost_per_1k=0.5))
        cheapest = cat.cheapest()
        assert cheapest is not None
        assert cheapest.model_id == "cheap"

    def test_cheapest_empty(self) -> None:
        cat = ModelCatalog()
        assert cat.cheapest() is None
