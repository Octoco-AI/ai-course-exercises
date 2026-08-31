using System.Text.Json;
using TinyAgent.Shared;
using Xunit;

namespace TinyAgent.Tests;

/// <summary>
/// The loop's contract, tested offline against a canned model.
/// </summary>
/// <remarks>
/// These cover the three mistakes the facilitator notes say account for most
/// failures in the room: forgetting to append the model's own turn, sending tool
/// results under the wrong role, and never terminating.
///
/// They run against <b>your</b> loop, via the same TINY_AGENT_IMPL switch the
/// tool tests use (see <see cref="Impl"/>), so they are red until step 1 is
/// done — that's the point. To watch them green against the worked solution:
///     TINY_AGENT_IMPL=reference dotnet test --filter AgentLoop
///
/// The tools they call are always the reference ones: these tests are about the
/// loop, and should not go red because step 2 is still unwritten.
/// </remarks>
public sealed class AgentLoopTests : IDisposable
{
    private readonly string _sandbox;

    public AgentLoopTests()
    {
        _sandbox = Path.Combine(Path.GetTempPath(), "tiny-agent-loop-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_sandbox);
        File.WriteAllText(Path.Combine(_sandbox, "hello.txt"), "hello world\n");
    }

    public void Dispose()
    {
        if (Directory.Exists(_sandbox)) Directory.Delete(_sandbox, recursive: true);
    }

    private async Task<(string Final, FakeGeminiHandler Handler)> RunAsync(params string[] turns)
    {
        var handler = new FakeGeminiHandler(turns);
        using var http = new HttpClient(handler);
        using var client = new GeminiClient("test-key", http);

        var tools = new Reference.ReferenceTools(_sandbox);
        var final = await AgentFactory.RunAsync(
            "do the thing", tools, client, model: "fake-model",
            cancellationToken: TestContext.Current.CancellationToken);

        return (final, handler);
    }

    [Fact]
    public async Task ReturnsTextWhenModelMakesNoToolCall()
    {
        var (final, handler) = await RunAsync(FakeGeminiHandler.TextTurn("All done."));

        Assert.Equal("All done.", final);
        Assert.Single(handler.Requests);
    }

    [Fact]
    public async Task RunsToolThenReturnsFinalText()
    {
        var (final, handler) = await RunAsync(
            FakeGeminiHandler.ToolCallTurn("read_file", new { path = "hello.txt" }),
            FakeGeminiHandler.TextTurn("The file says hello world."));

        Assert.Equal("The file says hello world.", final);
        Assert.Equal(2, handler.Requests.Count);

        // The second request must carry the tool's output back to the model.
        Assert.Contains("hello world", handler.Requests[1]);
    }

    [Fact]
    public async Task AppendsTheModelsOwnTurnBeforeTheToolResult()
    {
        // The single most-forgotten line in this exercise. If the model's turn
        // isn't appended, the model never sees that it already asked, and asks
        // again forever.
        var (_, handler) = await RunAsync(
            FakeGeminiHandler.ToolCallTurn("read_file", new { path = "hello.txt" }),
            FakeGeminiHandler.TextTurn("done"));

        using var doc = JsonDocument.Parse(handler.Requests[1]);
        var contents = doc.RootElement.GetProperty("contents");

        Assert.Equal(3, contents.GetArrayLength());       // user prompt, model turn, tool result
        Assert.Equal("user", contents[0].GetProperty("role").GetString());
        Assert.Equal("model", contents[1].GetProperty("role").GetString());
        Assert.True(contents[1].GetProperty("parts")[0].TryGetProperty("functionCall", out _));
    }

    [Fact]
    public async Task SendsToolResultsWithUserRole()
    {
        // Not "tool", not "function". About 15% of pairs try one of those.
        var (_, handler) = await RunAsync(
            FakeGeminiHandler.ToolCallTurn("read_file", new { path = "hello.txt" }),
            FakeGeminiHandler.TextTurn("done"));

        using var doc = JsonDocument.Parse(handler.Requests[1]);
        var toolTurn = doc.RootElement.GetProperty("contents")[2];

        Assert.Equal("user", toolTurn.GetProperty("role").GetString());
        Assert.True(toolTurn.GetProperty("parts")[0].TryGetProperty("functionResponse", out _));
    }

    [Fact]
    public async Task ToolErrorsGoBackToTheModelAsStrings()
    {
        // A tool failure must not kill the loop — the model gets to read it and retry.
        var (final, handler) = await RunAsync(
            FakeGeminiHandler.ToolCallTurn("read_file", new { path = "nope.txt" }),
            FakeGeminiHandler.TextTurn("That file doesn't exist."));

        Assert.Equal("That file doesn't exist.", final);
        Assert.Contains("ERROR:", handler.Requests[1]);
        Assert.Contains("does not exist", handler.Requests[1]);
    }

    [Fact]
    public async Task UnknownToolIsReportedRatherThanThrown()
    {
        var (final, handler) = await RunAsync(
            FakeGeminiHandler.ToolCallTurn("delete_everything", new { path = "." }),
            FakeGeminiHandler.TextTurn("I can't do that."));

        Assert.Equal("I can't do that.", final);
        Assert.Contains("unknown tool", handler.Requests[1]);
    }

    [Fact]
    public async Task StopsAtMaxTurns()
    {
        // A model that never stops calling tools must not loop forever.
        var turns = Enumerable
            .Range(0, 3)
            .Select(_ => FakeGeminiHandler.ToolCallTurn("read_file", new { path = "hello.txt" }))
            .ToArray();

        var handler = new FakeGeminiHandler(turns);
        using var http = new HttpClient(handler);
        using var client = new GeminiClient("test-key", http);

        var tools = new Reference.ReferenceTools(_sandbox);
        var final = await AgentFactory.RunAsync(
            "loop forever", tools, client, model: "fake-model", maxTurns: 3,
            cancellationToken: TestContext.Current.CancellationToken);

        Assert.StartsWith("ERROR:", final);
        Assert.Contains("did not finish within 3 turns", final);
        Assert.Equal(3, handler.Requests.Count);
    }
}
