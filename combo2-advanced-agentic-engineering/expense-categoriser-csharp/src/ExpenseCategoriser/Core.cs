using System.Globalization;
using System.Text.Json;

namespace ExpenseCategoriser;

/// <summary>
/// The categorisation logic.
/// </summary>
/// <remarks>
/// <para>
/// Deliberately pulls apart the pieces that matter for three-layer testing:
/// </para>
/// <list type="bullet">
/// <item><see cref="BuildPrompt"/> — pure function, unit-test with exact assertions.</item>
/// <item><see cref="ParseResponse"/> — pure function, unit-test.</item>
/// <item><see cref="ApplyConfidenceThreshold"/> — pure function, unit-test.</item>
/// <item><see cref="CategoriseAsync"/> — calls Gemini; integration-test with a
/// real key, mock at the LLM boundary for unit tests.</item>
/// </list>
/// <para>
/// Herman's blog "Testing the Untestable" says: test the deterministic parts
/// traditionally, test the AI boundary for contract conformance, and measure the
/// AI itself via evals at scale. This class is the code under test for all three.
/// </para>
/// </remarks>
public static class Core
{
    public const double DefaultConfidenceThreshold = 0.6;

    private const string SystemPromptTemplate = """
        You are an expense-categorisation assistant for a personal finance app.

        Given a transaction description and amount, pick the single best category from this list:

        {0}

        Respond with a JSON object of exactly this shape:

          {{"category": "<one of the categories above>", "confidence": <0.0-1.0>}}

        Rules:
        - Use only categories from the list above. No new categories.
        - "confidence" is your self-reported certainty. Use 0.9+ for obvious matches
          (grocery store -> Food & Dining), 0.5-0.7 for ambiguous cases, below 0.5
          for genuinely unclear items.
        - Do not explain. Do not add extra keys. Respond with JSON only.
        """;

    /// <summary>Build the user-turn prompt. Unit-tested for construction correctness.</summary>
    public static string BuildPrompt(string description, double amount) =>
        $"Transaction: \"{description}\"\nAmount: {amount.ToString("F2", CultureInfo.InvariantCulture)}";

    /// <summary>Render the system prompt with the canonical category list.</summary>
    public static string BuildSystemPrompt(IReadOnlyList<string>? categories = null)
    {
        categories ??= Categories.Canonical;
        var joined = string.Join("\n", categories.Select(c => $"  - {c}"));
        return string.Format(CultureInfo.InvariantCulture, SystemPromptTemplate, joined);
    }

    /// <summary>
    /// Parse and validate the model's JSON output.
    /// </summary>
    /// <exception cref="ContractViolationException">
    /// Malformed JSON, unknown category, or out-of-range confidence. The caller
    /// decides how to handle that (HTTP 502? Fall back to "Other"? Product policy).
    /// </exception>
    public static ModelResponse ParseResponse(string raw, IReadOnlyList<string>? validCategories = null)
    {
        validCategories ??= Categories.Canonical;

        JsonElement root;
        try
        {
            using var doc = JsonDocument.Parse(raw);
            root = doc.RootElement.Clone();
        }
        catch (JsonException ex)
        {
            throw new ContractViolationException($"model response is not valid JSON: {ex.Message}");
        }

        if (root.ValueKind != JsonValueKind.Object)
        {
            throw new ContractViolationException(
                $"model response must be a JSON object, got {root.ValueKind}");
        }

        if (!root.TryGetProperty("category", out var categoryElement) ||
            categoryElement.ValueKind != JsonValueKind.String)
        {
            throw new ContractViolationException("model response is missing required field: category");
        }

        if (!root.TryGetProperty("confidence", out var confidenceElement) ||
            !confidenceElement.TryGetDouble(out var confidence))
        {
            throw new ContractViolationException("model response is missing required field: confidence");
        }

        var category = categoryElement.GetString()!;
        if (!validCategories.Contains(category, StringComparer.Ordinal))
        {
            throw new ContractViolationException(
                $"model returned unknown category '{category}'; "
                + $"expected one of [{string.Join(", ", validCategories)}]");
        }

        if (confidence is < 0.0 or > 1.0)
        {
            throw new ContractViolationException($"confidence must be in [0, 1], got {confidence}");
        }

        return new ModelResponse(category, confidence);
    }

    /// <summary>
    /// Graceful degradation: if confidence is below the threshold, return the
    /// fallback category instead of the model's (uncertain) answer.
    /// </summary>
    /// <remarks>
    /// From Herman's blog: <c>if confidence &lt; threshold: show 'popular in
    /// similar situations'</c>. For expense categorisation the analogue is
    /// "Other", which the user can manually re-classify.
    /// </remarks>
    public static CategorisationOut ApplyConfidenceThreshold(
        ModelResponse response,
        double threshold,
        string fallbackCategory = Categories.Fallback) =>
        response.Confidence < threshold
            ? new CategorisationOut(fallbackCategory, response.Confidence, UsedFallback: true)
            : new CategorisationOut(response.Category, response.Confidence, UsedFallback: false);

    /// <summary>Categorise a single expense. The function three-layer-tested above.</summary>
    public static async Task<CategorisationOut> CategoriseAsync(
        string description,
        double amount,
        ILlmClient client,
        double? confidenceThreshold = null,
        CancellationToken cancellationToken = default)
    {
        var threshold = confidenceThreshold ?? ResolveThreshold();

        var systemPrompt = BuildSystemPrompt();
        var userPrompt = BuildPrompt(description, amount);

        var raw = await client.GenerateAsync(systemPrompt, userPrompt, cancellationToken)
                              .ConfigureAwait(false);

        var parsed = ParseResponse(raw);
        return ApplyConfidenceThreshold(parsed, threshold);
    }

    private static double ResolveThreshold()
    {
        var raw = Environment.GetEnvironmentVariable("CONFIDENCE_THRESHOLD");
        return double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var value)
            ? value
            : DefaultConfidenceThreshold;
    }
}

/// <summary>
/// Narrow interface so tests can substitute a fake without touching Gemini.
/// </summary>
/// <remarks>
/// This seam is the whole reason the unit tests need no API key and cost nothing.
/// M11 leans on it heavily — notice that the eval suite deliberately does NOT
/// use it, because evals measure the real model.
/// </remarks>
public interface ILlmClient
{
    /// <summary>Return the raw JSON string the model produced.</summary>
    Task<string> GenerateAsync(string systemPrompt, string userPrompt, CancellationToken cancellationToken = default);
}
