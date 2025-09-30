# Regression Testing with DeepEval

This directory contains LLM-based regression tests using the DeepEval framework to ensure chat functionality remains accurate and helpful throughout codebase changes.

## Overview

Traditional unit tests verify exact outputs, but LLM responses naturally vary in wording while maintaining correctness. DeepEval evaluates response **quality** rather than exact matches, using metrics like:

- **Answer Relevancy**: Does the response actually answer the question?
- **Hallucination**: Does the response contain facts not supported by the database query results?
- **Faithfulness**: Is the response grounded in the tool/query results?

## Running the Tests

```bash
# Run all regression tests
uv run pytest backend/tests/test_chat_regression.py -v

# Run specific test class
uv run pytest backend/tests/test_chat_regression.py::TestPlayerQueries -v

# Run single test
uv run pytest backend/tests/test_chat_regression.py::TestPlayerQueries::test_player_season_stats -v

# Run with detailed output
uv run pytest backend/tests/test_chat_regression.py -v -s
```

## Test Structure

### Test Classes

- **TestPlayerQueries**: Player statistics queries
- **TestTeamQueries**: Team performance and standings
- **TestGameQueries**: Game results and box scores (critical test: game details)
- **TestLeagueLeaderQueries**: Top performers and league leaders
- **TestComplexQueries**: Multi-step queries requiring context
- **TestResponseQuality**: Edge cases and error handling

### Critical Tests

The `test_game_details_with_stats` test is particularly important as it validates that game detail responses include:
- Basic game info (teams, scores, date)
- Individual player leaders (goals, assists, blocks, etc.)
- Team statistics (completion %, possession stats)

## Understanding Metrics

### Answer Relevancy (threshold: 0.7)
Measures if the response answers the user's question. A score of 0.7+ means the response is relevant.

**Example**:
- Query: "Who scored the most goals?"
- Good (0.9): "John Smith scored 45 goals this season"
- Bad (0.3): "The team played well this year"

### Hallucination (threshold: 0.5-0.7)
Measures if the response contains information not in the query results. Lower is better.

**Important Note**: In our sports stats system, the AI transforms raw SQL results into natural language. Some "hallucination" is acceptable as long as the core facts (numbers, names, teams) match the data. We use moderate thresholds (0.5-0.7) to allow natural language formatting while catching major fabrications.

**Example**:
- Context: `{"player": "Smith", "goals": 10}`
- Good (0.2): "Smith scored 10 goals"
- Acceptable (0.5): "Smith had an impressive 10-goal performance"
- Bad (0.9): "Smith scored 25 goals" (wrong number)

### Faithfulness (threshold: 0.7)
Measures if claims in the response can be inferred from the query results.

## Threshold Philosophy

Our thresholds are set to:
1. **Catch real problems**: Wrong stats, made-up players, incorrect facts
2. **Allow natural language**: The AI can format and explain data naturally
3. **Be practical**: Tests shouldn't fail on harmless variations in wording

### Recommended Thresholds

```python
# Lenient (for complex queries or queries that may not have data)
AnswerRelevancyMetric(threshold=0.5-0.6)
HallucinationMetric(threshold=0.7)

# Moderate (most queries)
AnswerRelevancyMetric(threshold=0.7)
HallucinationMetric(threshold=0.5-0.6)

# Strict (critical functionality like game details)
AnswerRelevancyMetric(threshold=0.8)
HallucinationMetric(threshold=0.4)
FaithfulnessMetric(threshold=0.7)
```

## Using Claude for Evaluation

The tests use Claude (not OpenAI) to evaluate responses via a custom `ClaudeModel` class. This ensures:
- Consistency with your production LLM
- No need for OpenAI API keys
- Use of your existing Anthropic API key

## Adding New Tests

To add a new regression test:

```python
def test_your_query(self, chat_helper, claude_model):
    """Test description."""
    test_case = chat_helper.create_test_case(
        input_query="Your question here",
        expected_keywords=["key", "words"],
    )

    relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
    hallucination_metric = HallucinationMetric(threshold=0.5, model=claude_model)

    assert_test(test_case, [relevancy_metric, hallucination_metric])
```

## Debugging Failed Tests

When a test fails, DeepEval provides a detailed reason:

```
AssertionError: Metrics: Hallucination (score: 0.8, threshold: 0.5, strict: False,
reason: The response mentions statistics that don't appear in the query results...)
```

The `reason` field is self-explaining - it tells you **why** the score is what it is, making it easy to identify real issues vs. threshold tuning needs.

## Benefits vs. Traditional Unit Tests

| Traditional Tests | DeepEval Regression Tests |
|------------------|---------------------------|
| Check exact outputs | Check response quality |
| Brittle - fail on small changes | Flexible - allow natural variation |
| Fast but limited | Slower but comprehensive |
| Test implementation | Test user experience |

Use DeepEval for:
- ✅ End-to-end chat functionality
- ✅ Ensuring stability through refactors
- ✅ Validating answer quality

Use traditional tests for:
- ✅ SQL query correctness
- ✅ Data processing logic
- ✅ API endpoint behavior
- ✅ Fast CI/CD pipelines

## Cost Considerations

DeepEval metrics use LLM calls for evaluation. Each test makes 2-3 API calls to Claude:
- ~$0.001-0.01 per test (Haiku model)
- Full suite (~15 tests): ~$0.02-0.15

Run these tests:
- Before major releases
- After significant refactors
- When debugging chat quality issues
- Not necessarily on every commit (use traditional tests for that)
