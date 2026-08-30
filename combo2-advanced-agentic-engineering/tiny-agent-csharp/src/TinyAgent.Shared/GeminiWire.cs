using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace TinyAgent.Shared;

// The Gemini REST wire format, as records. This is the whole API surface the
// agent needs — about 40 lines of DTOs and no SDK.
//
// Read this once and the shape of every function-calling API stops being
// mysterious: a list of turns, each turn a list of parts, each part either text
// or a function call. Anthropic and OpenAI differ in names, not in shape.

public sealed record GeminiRequest(
    [property: JsonPropertyName("contents")] IReadOnlyList<Content> Contents,
    [property: JsonPropertyName("tools")] IReadOnlyList<ToolDeclaration>? Tools = null,
    [property: JsonPropertyName("systemInstruction")] Content? SystemInstruction = null);

public sealed record Content(
    [property: JsonPropertyName("role")] string Role,
    [property: JsonPropertyName("parts")] IReadOnlyList<Part> Parts);

/// <summary>
/// One piece of a turn. Exactly one of the three properties is set.
/// </summary>
/// <remarks>
/// A part is text, OR a function call from the model, OR a function response
/// from you. Checking for null on the wrong one is the C# equivalent of the
/// Python original's "parts have .text XOR .function_call" footgun.
/// </remarks>
public sealed record Part(
    [property: JsonPropertyName("text")] string? Text = null,
    [property: JsonPropertyName("functionCall")] FunctionCall? FunctionCall = null,
    [property: JsonPropertyName("functionResponse")] FunctionResponse? FunctionResponse = null);

public sealed record FunctionCall(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("args")] JsonObject? Args = null);

public sealed record FunctionResponse(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("response")] JsonObject Response);

public sealed record ToolDeclaration(
    [property: JsonPropertyName("functionDeclarations")] IReadOnlyList<FunctionDeclaration> FunctionDeclarations);

public sealed record FunctionDeclaration(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("description")] string Description,
    [property: JsonPropertyName("parameters")] JsonObject Parameters);

public sealed record GeminiResponse(
    [property: JsonPropertyName("candidates")] IReadOnlyList<Candidate>? Candidates = null,
    [property: JsonPropertyName("promptFeedback")] JsonObject? PromptFeedback = null);

public sealed record Candidate(
    [property: JsonPropertyName("content")] Content? Content = null,
    [property: JsonPropertyName("finishReason")] string? FinishReason = null);

public static class GeminiJson
{
    /// <summary>Shared serializer options. Null properties are omitted — the API rejects some explicit nulls.</summary>
    public static readonly JsonSerializerOptions Options = new()
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = false,
    };
}
