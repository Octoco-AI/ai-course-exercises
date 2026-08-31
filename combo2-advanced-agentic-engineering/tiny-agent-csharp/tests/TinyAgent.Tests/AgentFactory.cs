using TinyAgent.Shared;

namespace TinyAgent.Tests;

/// <summary>
/// The agent loop under test — the same switch as <see cref="ToolsFactory"/>,
/// so step 1 gets a test suite too.
/// </summary>
public static class AgentFactory
{
    public static Task<string> RunAsync(
        string userPrompt,
        ITools tools,
        GeminiClient client,
        string? model = null,
        int maxTurns = 20,
        Action<AgentEvent>? onEvent = null,
        CancellationToken cancellationToken = default) =>
        Impl.Selected() == "reference"
            ? Reference.Agent.RunAsync(userPrompt, tools, client, model, maxTurns, onEvent, cancellationToken)
            : Starter.Agent.RunAsync(userPrompt, tools, client, model, maxTurns, onEvent, cancellationToken);
}
