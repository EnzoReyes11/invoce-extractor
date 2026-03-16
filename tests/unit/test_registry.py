from __future__ import annotations

import pytest

from pdf_data_extraction_agent.extractors.registry import get_strategy
from pdf_data_extraction_agent.extractors.generic import GENERIC_STRATEGY
from pdf_data_extraction_agent.extractors.claro import CLARO_STRATEGY


class TestGetStrategy:
    def test_exact_match(self):
        assert get_strategy("claro") == CLARO_STRATEGY

    def test_case_insensitive_upper(self):
        assert get_strategy("CLARO") == CLARO_STRATEGY

    def test_case_insensitive_mixed(self):
        assert get_strategy("Claro") == CLARO_STRATEGY

    def test_partial_match_full_name(self):
        assert get_strategy("Claro Argentina") == CLARO_STRATEGY

    def test_partial_match_embedded(self):
        assert get_strategy("Personal Claro Plan") == CLARO_STRATEGY

    def test_no_match_returns_generic(self):
        assert get_strategy("TeleCom XYZ") == GENERIC_STRATEGY

    def test_none_returns_generic(self):
        assert get_strategy(None) == GENERIC_STRATEGY

    def test_empty_string_returns_generic(self):
        assert get_strategy("") == GENERIC_STRATEGY

    def test_generic_strategy_name(self):
        strategy = get_strategy(None)
        assert strategy.name == "generic"

    def test_claro_strategy_name(self):
        strategy = get_strategy("Claro Argentina")
        assert strategy.name == "claro"
