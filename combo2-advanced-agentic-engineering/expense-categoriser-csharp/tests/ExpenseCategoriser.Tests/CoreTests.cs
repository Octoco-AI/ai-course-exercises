using ExpenseCategoriser;
using Xunit;

namespace ExpenseCategoriser.Tests;

/// <summary>
/// Layer 1 — unit tests over the deterministic parts. No LLM, no key, no cost.
/// </summary>
/// <remarks>
/// This is the layer most teams skip when they build an AI feature, on the
/// grounds that "it's all AI, you can't test it". Look how much of this file
/// tests ordinary code with exact assertions. That is the point of pulling
/// <c>BuildPrompt</c>, <c>ParseResponse</c> and <c>ApplyConfidenceThreshold</c>
/// apart in the first place.
/// </remarks>
public class CoreTests
{
    // ---- BuildPrompt --------------------------------------------------------

    [Fact]
    public void BuildPrompt_FormatsDescriptionAndAmount()
    {
        var prompt = Core.BuildPrompt("Whole Foods Market", 78.23);

        Assert.Equal("Transaction: \"Whole Foods Market\"\nAmount: 78.23", prompt);
    }

    [Fact]
    public void BuildPrompt_AlwaysUsesTwoDecimalPlaces()
    {
        Assert.Contains("Amount: 5.00", Core.BuildPrompt("Coffee", 5));
        Assert.Contains("Amount: -20.00", Core.BuildPrompt("Refund", -20));
    }

    [Fact]
    public void BuildSystemPrompt_ListsEveryCanonicalCategory()
    {
        var prompt = Core.BuildSystemPrompt();

        foreach (var category in Categories.Canonical)
        {
            Assert.Contains($"  - {category}", prompt);
        }
    }

    // ---- ParseResponse ------------------------------------------------------

    [Fact]
    public void ParseResponse_ValidJson()
    {
        var parsed = Core.ParseResponse("""{"category": "Food & Dining", "confidence": 0.95}""");

        Assert.Equal("Food & Dining", parsed.Category);
        Assert.Equal(0.95, parsed.Confidence, precision: 5);
    }

    [Fact]
    public void ParseResponse_RejectsMalformedJson()
    {
        var ex = Assert.Throws<ContractViolationException>(
            () => Core.ParseResponse("not json at all"));

        Assert.Contains("not valid JSON", ex.Message);
    }

    [Fact]
    public void ParseResponse_RejectsNonObject()
    {
        var ex = Assert.Throws<ContractViolationException>(() => Core.ParseResponse("[1, 2, 3]"));

        Assert.Contains("must be a JSON object", ex.Message);
    }

    [Fact]
    public void ParseResponse_RejectsMissingFields()
    {
        Assert.Throws<ContractViolationException>(
            () => Core.ParseResponse("""{"category": "Food & Dining"}"""));

        Assert.Throws<ContractViolationException>(
            () => Core.ParseResponse("""{"confidence": 0.9}"""));
    }

    [Fact]
    public void ParseResponse_RejectsUnknownCategory()
    {
        // The model inventing a category is the most common contract violation
        // in practice, and the easiest to miss without this assertion.
        var ex = Assert.Throws<ContractViolationException>(
            () => Core.ParseResponse("""{"category": "Snacks", "confidence": 0.9}"""));

        Assert.Contains("unknown category", ex.Message);
        Assert.Contains("Snacks", ex.Message);
    }

    [Theory]
    [InlineData(-0.1)]
    [InlineData(1.5)]
    public void ParseResponse_RejectsOutOfRangeConfidence(double confidence)
    {
        var ex = Assert.Throws<ContractViolationException>(
            () => Core.ParseResponse($$"""{"category": "Other", "confidence": {{confidence}}}"""));

        Assert.Contains("confidence must be in [0, 1]", ex.Message);
    }

    // ---- ApplyConfidenceThreshold ------------------------------------------

    [Fact]
    public void ApplyConfidenceThreshold_KeepsConfidentAnswer()
    {
        var result = Core.ApplyConfidenceThreshold(new ModelResponse("Travel", 0.85), threshold: 0.6);

        Assert.Equal("Travel", result.Category);
        Assert.False(result.UsedFallback);
    }

    [Fact]
    public void ApplyConfidenceThreshold_FallsBackBelowThreshold()
    {
        var result = Core.ApplyConfidenceThreshold(new ModelResponse("Travel", 0.4), threshold: 0.6);

        Assert.Equal("Other", result.Category);
        Assert.True(result.UsedFallback);
        // The original confidence is preserved — the caller may want to show it.
        Assert.Equal(0.4, result.Confidence, precision: 5);
    }

    [Fact]
    public void ApplyConfidenceThreshold_BoundaryIsInclusive()
    {
        // Exactly at the threshold counts as confident. Worth pinning: an
        // off-by-one here silently changes behaviour for a whole band of inputs.
        var result = Core.ApplyConfidenceThreshold(new ModelResponse("Housing", 0.6), threshold: 0.6);

        Assert.Equal("Housing", result.Category);
        Assert.False(result.UsedFallback);
    }

    // ---- CategoriseAsync (mocked at the LLM boundary) ----------------------

    [Fact]
    public async Task CategoriseAsync_HappyPath()
    {
        var client = FakeLlmClient.Returning("Food & Dining", 0.95);

        var result = await Core.CategoriseAsync("Starbucks", 5.45, client, confidenceThreshold: 0.6,
            cancellationToken: TestContext.Current.CancellationToken);

        Assert.Equal("Food & Dining", result.Category);
        Assert.False(result.UsedFallback);
        Assert.Equal(1, client.CallCount);
    }

    [Fact]
    public async Task CategoriseAsync_PassesThePromptsThrough()
    {
        var client = FakeLlmClient.Returning("Other", 0.9);

        await Core.CategoriseAsync("Starbucks", 5.45, client, confidenceThreshold: 0.6,
            cancellationToken: TestContext.Current.CancellationToken);

        Assert.Contains("Starbucks", client.LastUserPrompt);
        Assert.Contains("Food & Dining", client.LastSystemPrompt);
    }

    [Fact]
    public async Task CategoriseAsync_SurfacesContractViolations()
    {
        var client = new FakeLlmClient("{ nonsense");

        await Assert.ThrowsAsync<ContractViolationException>(
            () => Core.CategoriseAsync("Starbucks", 5.45, client,
                cancellationToken: TestContext.Current.CancellationToken));
    }
}
