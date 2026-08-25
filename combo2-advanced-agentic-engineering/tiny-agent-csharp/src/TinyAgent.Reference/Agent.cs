using System.Text;
using System.Text.Json.Nodes;
using TinyAgent.Shared;

namespace TinyAgent.Reference;

/// <summary>
/// The agent loop — complete worked solution.
/// </summary>
/// <remarks>
/// <para>Thesis (Thorsten Ball, ampcode.com): <i>It's an LLM, a loop, and enough tokens.</i></para>
/// <para>What the loop does, in one glance:</para>
/// <code>
/// contents = [user_prompt]
/// while turn &lt; maxTurns:
///     response = gemini.generate(contents, tools)
///     contents.Add(response.content)          // the most-forgotten line
///     calls = function calls in the response
///     if no calls: return the text            // done
///     foreach call: contents.Add(functionResponse)
/// </code>
/// <para>
/// Note it is <c>async</c>. The Python original is deliberately synchronous —
/// its facilitator notes say "not a chance to teach asyncio". In .NET every
/// HTTP call is a <see cref="Task"/>, so <c>await</c> is unavoidable here.
/// It is plumbing, not the lesson: read past it and look at the loop.
/// </para>
/// </remarks>
public static class Agent
{
    public const string SystemInstruction = """
        You are a careful coding assistant working inside a small
        code repository. You have three tools: read_file, list_files, and edit_file.

        Workflow:
        1. Explore first. Use list_files and read_file to build an understanding before editing.
        2. Edit sparingly. One edit per logical change. Use enough surrounding context in
           old_str so it matches exactly once.
        3. Report what you did in plain prose when you are finished. Do not call any tool on
           the final turn — that's how you signal you're done.
        4. If a tool returns a string starting with "ERROR:", read the error carefully and
           adjust your approach. Don't retry the same call blindly.
        """;

    public static async Task<string> RunAsync(
        string userPrompt,
        ITools tools,
        GeminiClient client,
        string? model = null,
        int maxTurns = 20,
        Action<AgentEvent>? onEvent = null,
        CancellationToken cancellationToken = default)
    {
        model ??= DotEnv.Model();

        // Conversation state. Gemini's "contents" is an ordered list of turns
        // alternating between role "user" and role "model". Tool results go back
        // as a *user* turn whose parts are functionResponse parts.
        var contents = new List<Content>
        {
            new("user", new[] { new Part(Text: userPrompt) }),
        };

        var declarations = new[] { ToolSchemas.All() };
        var systemInstruction = new Content("user", new[] { new Part(Text: SystemInstruction) });

        for (var turn = 1; turn <= maxTurns; turn++)
        {
            onEvent?.Invoke(new AgentEvent.TurnStart(turn));

            var request = new GeminiRequest(contents, declarations, systemInstruction);
            var response = await client.GenerateContentAsync(model, request, cancellationToken)
                                      .ConfigureAwait(false);

            var candidate = response.Candidates?.FirstOrDefault();
            if (candidate?.Content is null)
            {
                return $"ERROR: model returned no content (finishReason: {candidate?.FinishReason ?? "none"})";
            }

            // Append the model's turn BEFORE doing anything else. Forget this and
            // the model re-reads a context that never contains its own tool calls,
            // so it asks for the same thing forever. It is the #1 failure here.
            contents.Add(candidate.Content);

            var calls = (candidate.Content.Parts ?? Array.Empty<Part>())
                .Where(p => p.FunctionCall is not null)
                .Select(p => p.FunctionCall!)
                .ToList();

            if (calls.Count == 0)
            {
                // No tool calls -> the model signalled it is done.
                var finalText = string.Concat(
                    (candidate.Content.Parts ?? Array.Empty<Part>()).Select(p => p.Text ?? string.Empty));
                onEvent?.Invoke(new AgentEvent.Final(finalText, turn));
                return finalText;
            }

            // Execute every call and collect the responses.
            var responseParts = new List<Part>();
            foreach (var call in calls)
            {
                onEvent?.Invoke(new AgentEvent.ToolCall(call.Name, PreviewArgs(call.Args)));

                var result = Dispatch(tools, call);

                onEvent?.Invoke(new AgentEvent.ToolResult(call.Name, result));
                responseParts.Add(new Part(FunctionResponse: new FunctionResponse(
                    call.Name,
                    new JsonObject { ["result"] = result })));
            }

            // Send all tool responses back in a single user turn.
            contents.Add(new Content("user", responseParts));
        }

        return $"ERROR: agent did not finish within {maxTurns} turns";
    }

    /// <summary>
    /// Route one function call to a tool. Every failure path returns a string —
    /// nothing thrown here reaches the loop.
    /// </summary>
    public static string Dispatch(ITools tools, FunctionCall call)
    {
        try
        {
            return call.Name switch
            {
                ToolSchemas.ReadFileName => tools.ReadFile(RequiredArg(call, "path")),
                ToolSchemas.ListFilesName => tools.ListFiles(OptionalArg(call, "path") ?? ".").ToModelString(),
                ToolSchemas.EditFileName => tools.EditFile(
                    RequiredArg(call, "path"),
                    RequiredArg(call, "old_str"),
                    RequiredArg(call, "new_str")),
                _ => $"ERROR: unknown tool '{call.Name}'",
            };
        }
        catch (ArgumentException ex)
        {
            return $"ERROR: bad arguments to {call.Name}: {ex.Message}";
        }
        catch (Exception ex)
        {
            // Surface any tool failure to the model rather than killing the loop.
            return $"ERROR: {ex.GetType().Name}: {ex.Message}";
        }
    }

    private static string RequiredArg(FunctionCall call, string name) =>
        OptionalArg(call, name) ?? throw new ArgumentException($"missing required argument '{name}'");

    private static string? OptionalArg(FunctionCall call, string name)
    {
        if (call.Args is null) return null;
        return call.Args.TryGetPropertyValue(name, out var node) && node is not null
            ? node.GetValue<string>()
            : null;
    }

    private static string PreviewArgs(JsonObject? args)
    {
        if (args is null || args.Count == 0) return string.Empty;

        var sb = new StringBuilder();
        foreach (var (key, value) in args)
        {
            if (sb.Length > 0) sb.Append(", ");
            sb.Append(key).Append('=').Append(value?.ToJsonString() ?? "null");
        }

        var preview = sb.ToString();
        return preview.Length > 120 ? preview[..117] + "..." : preview;
    }
}
