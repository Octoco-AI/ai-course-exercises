using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace ExpenseCategoriser;

/// <summary>Request/response contracts + the canonical category list.</summary>
public static class Categories
{
    /// <summary>
    /// Keep this list short and stable — the prompt enumerates it. Don't
    /// reshuffle without re-running the eval baseline; label order can subtly
    /// affect the LLM.
    /// </summary>
    public static readonly string[] Canonical =
    [
        "Food & Dining",
        "Transportation",
        "Shopping",
        "Entertainment",
        "Healthcare",
        "Utilities",
        "Housing",
        "Travel",
        "Personal Care",
        "Subscriptions",
        "Education",
        "Gifts & Donations",
        "Income",
        "Other",
    ];

    public const string Fallback = "Other";
}

/// <summary>What the API caller sends.</summary>
public sealed record ExpenseIn
{
    /// <summary>Transaction description as it appears on the statement.</summary>
    [Required, MinLength(1), MaxLength(500)]
    [JsonPropertyName("description")]
    public required string Description { get; init; }

    /// <summary>Transaction amount in the user's currency. Negative = credit.</summary>
    [JsonPropertyName("amount")]
    public required double Amount { get; init; }
}

/// <summary>What the API returns.</summary>
public sealed record CategorisationOut(
    [property: JsonPropertyName("category")] string Category,
    [property: JsonPropertyName("confidence")] double Confidence,
    /// <summary>
    /// True when the model's confidence fell below the threshold and we returned
    /// "Other" as a fallback. Note this is a SUCCESSFUL response, not an error.
    /// </summary>
    [property: JsonPropertyName("used_fallback")] bool UsedFallback);

/// <summary>
/// The schema we ask Gemini to produce. Kept separate from
/// <see cref="CategorisationOut"/> so we can wrap the raw model output with our
/// fallback logic before returning it.
/// </summary>
public sealed record ModelResponse(
    [property: JsonPropertyName("category")] string Category,
    [property: JsonPropertyName("confidence")] double Confidence);

/// <summary>
/// Raised when the model's output violates the contract we asked for.
/// </summary>
/// <remarks>
/// This is the "the model started misbehaving" signal that the CE pipeline in
/// M12 watches for. It maps to HTTP 502, not 500 — the service is fine, the
/// model isn't.
/// </remarks>
public sealed class ContractViolationException(string message) : Exception(message);
