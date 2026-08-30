namespace TinyAgent.Shared;

/// <summary>
/// Shared console entrypoint. GIVEN — no changes needed.
/// </summary>
public static class Cli
{
    /// <summary>Print one line per meaningful action, so the loop is visible as it runs.</summary>
    public static void PrintEvent(AgentEvent evt)
    {
        switch (evt)
        {
            case AgentEvent.ToolCall call:
                Console.WriteLine($"  -> {call.Name}({call.ArgsPreview})");
                break;
            case AgentEvent.ToolResult result:
                var text = result.Result;
                if (text.Length > 200) text = text[..197] + "...";
                Console.WriteLine($"     {text.ReplaceLineEndings(" | ")}");
                break;
        }
    }

    /// <summary>
    /// Wire up env, client and tools, then run one prompt. Returns a process exit code.
    /// </summary>
    public static async Task<int> RunAsync(
        string[] args,
        string usage,
        Func<string, ITools> makeTools,
        Func<string, ITools, GeminiClient, Action<AgentEvent>, Task<string>> run)
    {
        if (args.Length == 0)
        {
            Console.Error.WriteLine(usage);
            return 1;
        }

        DotEnv.Load();

        var apiKey = DotEnv.ApiKey();
        if (string.IsNullOrWhiteSpace(apiKey) || apiKey == "your_gemini_api_key_here")
        {
            Console.Error.WriteLine("ERROR: GOOGLE_API_KEY is not set. Copy .env.example to .env and paste your key.");
            return 2;
        }

        // The sandbox root is wherever you started the agent — same rule as the
        // Python version, where it is Path.cwd().
        var tools = makeTools(Directory.GetCurrentDirectory());
        using var client = new GeminiClient(apiKey);

        try
        {
            var final = await run(string.Join(' ', args), tools, client, PrintEvent).ConfigureAwait(false);
            Console.WriteLine();
            Console.WriteLine(final);
            return 0;
        }
        catch (NotImplementedException ex)
        {
            Console.Error.WriteLine($"Not implemented yet: {ex.Message}");
            return 3;
        }
        catch (HttpRequestException ex)
        {
            Console.Error.WriteLine($"ERROR: {ex.Message}");
            return 4;
        }
    }
}
