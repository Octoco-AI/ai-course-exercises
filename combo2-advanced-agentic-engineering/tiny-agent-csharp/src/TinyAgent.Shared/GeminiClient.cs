using System.Net.Http.Json;
using System.Text.Json;

namespace TinyAgent.Shared;

/// <summary>
/// A ~50-line Gemini client built on <see cref="HttpClient"/>. No SDK.
/// </summary>
/// <remarks>
/// <para>
/// The Python version of this exercise uses the <c>google-genai</c> SDK and has
/// to pass <c>automatic_function_calling=AutomaticFunctionCallingConfig(disable=True)</c>
/// to stop the SDK running the tools for you and handing back only the final
/// text. At the REST layer there is nothing to disable: <b>the loop is always
/// yours</b>. That is the same lesson, arrived at from the other direction.
/// </para>
/// <para>
/// There is no first-party Google GenAI SDK for .NET. That turns out to be a
/// gift for this exercise — you can see the entire protocol.
/// </para>
/// </remarks>
public sealed class GeminiClient : IDisposable
{
    public const string DefaultModel = "gemini-3.1-flash-lite";
    private const string BaseUrl = "https://generativelanguage.googleapis.com/v1beta/models";

    private readonly HttpClient _http;
    private readonly string _apiKey;
    private readonly bool _ownsHttpClient;

    public GeminiClient(string apiKey, HttpClient? http = null)
    {
        if (string.IsNullOrWhiteSpace(apiKey))
        {
            throw new InvalidOperationException(
                "GOOGLE_API_KEY is not set. Copy .env.example to .env and paste your key.");
        }

        _apiKey = apiKey;
        _ownsHttpClient = http is null;
        _http = http ?? new HttpClient { Timeout = TimeSpan.FromSeconds(120) };
    }

    /// <summary>One round-trip to the model.</summary>
    public async Task<GeminiResponse> GenerateContentAsync(
        string model,
        GeminiRequest request,
        CancellationToken cancellationToken = default)
    {
        var url = $"{BaseUrl}/{model}:generateContent";

        using var message = new HttpRequestMessage(HttpMethod.Post, url)
        {
            Content = JsonContent.Create(request, options: GeminiJson.Options),
        };
        // The key travels in a header, not the query string, so it stays out of logs.
        message.Headers.Add("x-goog-api-key", _apiKey);

        using var response = await _http.SendAsync(message, cancellationToken).ConfigureAwait(false);
        var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);

        if (!response.IsSuccessStatusCode)
        {
            // 429 on the free tier is common and worth naming explicitly —
            // it is the single most likely thing to go wrong in the room.
            var hint = response.StatusCode == System.Net.HttpStatusCode.TooManyRequests
                ? " (free-tier rate limit — wait a few seconds and retry)"
                : string.Empty;
            throw new HttpRequestException(
                $"Gemini returned {(int)response.StatusCode} {response.StatusCode}{hint}: {body}");
        }

        return JsonSerializer.Deserialize<GeminiResponse>(body, GeminiJson.Options)
               ?? new GeminiResponse();
    }

    public void Dispose()
    {
        if (_ownsHttpClient) _http.Dispose();
    }
}
