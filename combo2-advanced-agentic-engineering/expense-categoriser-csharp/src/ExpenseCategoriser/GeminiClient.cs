using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace ExpenseCategoriser;

/// <summary>
/// Thin Gemini client over <see cref="HttpClient"/>. No SDK.
/// </summary>
/// <remarks>
/// There is no first-party Google GenAI SDK for .NET, so this talks to the REST
/// API directly — about 40 lines. The same choice as the tiny-agent exercise,
/// for the same reason: you can see the whole protocol.
///
/// Two settings matter for a classifier and are easy to miss:
/// <list type="bullet">
/// <item><c>responseMimeType: "application/json"</c> — ask for JSON rather than
/// hoping for it. Halves the contract violations on its own.</item>
/// <item><c>temperature: 0.1</c> — this is classification; we want
/// near-determinism, not creativity.</item>
/// </list>
/// </remarks>
public sealed class GeminiClient : ILlmClient, IDisposable
{
    public const string DefaultModel = "gemini-3.1-flash-lite";
    private const string BaseUrl = "https://generativelanguage.googleapis.com/v1beta/models";

    private readonly HttpClient _http;
    private readonly string? _apiKey;
    private readonly string _model;
    private readonly bool _ownsHttpClient;

    public GeminiClient(string? apiKey = null, string? model = null, HttpClient? http = null)
    {
        _apiKey = apiKey ?? Environment.GetEnvironmentVariable("GOOGLE_API_KEY");
        _model = model
                 ?? Environment.GetEnvironmentVariable("GEMINI_MODEL")
                 ?? DefaultModel;
        _ownsHttpClient = http is null;
        _http = http ?? new HttpClient { Timeout = TimeSpan.FromSeconds(60) };
    }

    public async Task<string> GenerateAsync(
        string systemPrompt,
        string userPrompt,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(_apiKey))
        {
            // A configuration problem, not a model problem — the API maps this
            // to 500, where a contract violation maps to 502.
            throw new InvalidOperationException(
                "GOOGLE_API_KEY is not set. Either add it to .env or pass apiKey explicitly.");
        }

        var payload = new JsonObject
        {
            ["contents"] = new JsonArray(
                new JsonObject
                {
                    ["role"] = "user",
                    ["parts"] = new JsonArray(new JsonObject { ["text"] = userPrompt }),
                }),
            ["systemInstruction"] = new JsonObject
            {
                ["parts"] = new JsonArray(new JsonObject { ["text"] = systemPrompt }),
            },
            ["generationConfig"] = new JsonObject
            {
                ["responseMimeType"] = "application/json",
                ["temperature"] = 0.1,
            },
        };

        using var message = new HttpRequestMessage(HttpMethod.Post, $"{BaseUrl}/{_model}:generateContent")
        {
            Content = JsonContent.Create(payload),
        };
        message.Headers.Add("x-goog-api-key", _apiKey);

        using var response = await _http.SendAsync(message, cancellationToken).ConfigureAwait(false);
        var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);

        if (!response.IsSuccessStatusCode)
        {
            var hint = response.StatusCode == System.Net.HttpStatusCode.TooManyRequests
                ? " (free-tier rate limit — wait a few seconds and retry)"
                : string.Empty;
            throw new HttpRequestException(
                $"Gemini returned {(int)response.StatusCode} {response.StatusCode}{hint}: {body}");
        }

        return ExtractText(body);
    }

    /// <summary>Pull the text out of the first candidate. Returns "" if there isn't one.</summary>
    private static string ExtractText(string body)
    {
        using var doc = JsonDocument.Parse(body);

        if (!doc.RootElement.TryGetProperty("candidates", out var candidates) ||
            candidates.GetArrayLength() == 0)
        {
            return string.Empty;
        }

        if (!candidates[0].TryGetProperty("content", out var content) ||
            !content.TryGetProperty("parts", out var parts))
        {
            return string.Empty;
        }

        var text = string.Concat(
            parts.EnumerateArray()
                 .Select(p => p.TryGetProperty("text", out var t) ? t.GetString() ?? "" : ""));

        return text;
    }

    public void Dispose()
    {
        if (_ownsHttpClient) _http.Dispose();
    }
}
