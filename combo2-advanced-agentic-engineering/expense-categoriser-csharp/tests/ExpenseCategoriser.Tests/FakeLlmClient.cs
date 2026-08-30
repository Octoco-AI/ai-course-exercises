using ExpenseCategoriser;

namespace ExpenseCategoriser.Tests;

/// <summary>
/// A canned LLM. The seam that makes the unit and API layers free and instant.
/// </summary>
/// <remarks>
/// Layer 1 (unit) and layer 2 (API contract) never call a real model — they test
/// OUR code. Layer 3 (evals) never uses this — it measures the model. Mixing the
/// two up is the single most common mistake when teams first add evals.
/// </remarks>
public sealed class FakeLlmClient(string response) : ILlmClient
{
    public string? LastSystemPrompt { get; private set; }
    public string? LastUserPrompt { get; private set; }
    public int CallCount { get; private set; }

    public Task<string> GenerateAsync(
        string systemPrompt, string userPrompt, CancellationToken cancellationToken = default)
    {
        LastSystemPrompt = systemPrompt;
        LastUserPrompt = userPrompt;
        CallCount += 1;
        return Task.FromResult(response);
    }

    public static FakeLlmClient Returning(string category, double confidence) =>
        new($$"""{"category": "{{category}}", "confidence": {{confidence}}}""");
}

/// <summary>An LLM client that always throws — for testing the configuration-error path.</summary>
public sealed class ThrowingLlmClient(Exception exception) : ILlmClient
{
    public Task<string> GenerateAsync(
        string systemPrompt, string userPrompt, CancellationToken cancellationToken = default) =>
        Task.FromException<string>(exception);
}
