using TinyAgent.Shared;
using TinyAgent.Starter;

return await Cli.RunAsync(
    args,
    usage: """Usage: dotnet run --project ../TinyAgent.Starter -- "<your prompt>" """,
    makeTools: root => new StarterTools(root),
    run: (prompt, tools, client, onEvent) =>
        Agent.RunAsync(prompt, tools, client, onEvent: onEvent));
