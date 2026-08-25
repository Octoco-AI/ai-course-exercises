using System.Net;
using System.Text;
using System.Text.Json;
using TinyAgent.Shared;
using Xunit;

namespace TinyAgent.Tests;

/// <summary>
/// A canned Gemini that replays scripted turns, so the loop can be tested
/// without an API key or a cent of spend.
/// </summary>
/// <remarks>
/// Also records every request body, which is how the tests below assert on what
/// the loop actually sent back — the part you cannot see from the outside.
/// </remarks>
public sealed class FakeGeminiHandler : HttpMessageHandler
{
    private readonly Queue<string> _responses;

    public List<string> Requests { get; } = new();

    public FakeGeminiHandler(params string[] responseBodies) =>
        _responses = new Queue<string>(responseBodies);

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request, CancellationToken cancellationToken)
    {
        Requests.Add(request.Content is null
            ? string.Empty
            : await request.Content.ReadAsStringAsync(cancellationToken));

        var body = _responses.Count > 0
            ? _responses.Dequeue()
            : throw new InvalidOperationException(
                "FakeGemini ran out of scripted responses — the loop asked for more turns than expected.");

        return new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(body, Encoding.UTF8, "application/json"),
        };
    }

    // ---- helpers for building scripted turns --------------------------------

    public static string TextTurn(string text) =>
        Candidate("{\"text\": " + Json(text) + "}");

    public static string ToolCallTurn(string name, object args) =>
        Candidate("{\"functionCall\": {\"name\": " + Json(name)
                  + ", \"args\": " + JsonSerializer.Serialize(args) + "}}");

    private static string Candidate(string part) =>
        "{\"candidates\": [{\"content\": {\"role\": \"model\", \"parts\": [" + part + "]}}]}";

    private static string Json(string value) => JsonSerializer.Serialize(value);
}
