using System.Text;
using System.Text.Json.Nodes;
using TinyAgent.Shared;

namespace TinyAgent.Starter;

/// <summary>
/// The agent loop. YOU WRITE THIS (step 1).
/// </summary>
/// <remarks>
/// <para>Thesis (Thorsten Ball, ampcode.com): <i>It's an LLM, a loop, and enough tokens.</i></para>
/// <para>The shape of the loop you're going to write:</para>
/// <code>
/// contents = [userPrompt]
/// for turn in 1..maxTurns:
///     response = await client.GenerateContentAsync(model, request)
///     contents.Add(candidate.Content)          // don't forget this line
///     calls = parts where FunctionCall is not null
///     if no calls: return the joined text      // done
///     foreach call: Dispatch it, append a functionResponse part
///     contents.Add(new Content("user", responseParts))
/// </code>
/// <para>
/// Yes, it's <c>async</c>. Every HTTP call in .NET is a <see cref="Task"/>, so
/// <c>await</c> is unavoidable. It is plumbing, not the lesson.
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

    // -------------------------------------------------------------------------
    // STEP 1 — implement RunAsync
    // -------------------------------------------------------------------------
    /// <summary>
    /// Run the agent loop until the model returns a final answer.
    /// </summary>
    /// <remarks>
    /// Hints — everything you need is in <c>TinyAgent.Shared</c>:
    /// <list type="bullet">
    /// <item>Build a turn: <c>new Content("user", new[] { new Part(Text: userPrompt) })</c></item>
    /// <item>Build the request: <c>new GeminiRequest(contents, new[] { ToolSchemas.All() }, systemInstruction)</c></item>
    /// <item>Call the model: <c>await client.GenerateContentAsync(model, request, cancellationToken)</c></item>
    /// <item>The model's turn: <c>response.Candidates?.FirstOrDefault()?.Content</c></item>
    /// <item>Function calls live in <c>content.Parts</c> where <c>part.FunctionCall is not null</c></item>
    /// <item>Send a result back: <c>new Part(FunctionResponse: new FunctionResponse(name, new JsonObject { ["result"] = result }))</c></item>
    /// <item>Tool results go back with role <b>"user"</b>, not "tool" and not "function"</item>
    /// <item>Termination: a turn with no function-call parts</item>
    /// <item><see cref="Dispatch"/> below is written for you — call it, don't rewrite it</item>
    /// </list>
    /// Start with the simplest version that handles the exploration prompts
    /// (TODO.md items 1 and 2), then try the bug-fix prompt (item 3).
    /// </remarks>
    public static Task<string> RunAsync(
        string userPrompt,
        ITools tools,
        GeminiClient client,
        string? model = null,
        int maxTurns = 20,
        Action<AgentEvent>? onEvent = null,
        CancellationToken cancellationToken = default)
    {
        model ??= DotEnv.Model();

        // TODO: Step 1 — write the loop.
        throw new NotImplementedException("Implement RunAsync for step 1.");
    }

    // ---- given below this line — no changes needed -------------------------

    /// <summary>
    /// Route one function call to a tool. Every failure path returns a string.
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
            return $"ERROR: {ex.GetType().Name}: {ex.Message}";
        }
    }

    public static string RequiredArg(FunctionCall call, string name) =>
        OptionalArg(call, name) ?? throw new ArgumentException($"missing required argument '{name}'");

    public static string? OptionalArg(FunctionCall call, string name)
    {
        if (call.Args is null) return null;
        return call.Args.TryGetPropertyValue(name, out var node) && node is not null
            ? node.GetValue<string>()
            : null;
    }

    public static string PreviewArgs(JsonObject? args)
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
