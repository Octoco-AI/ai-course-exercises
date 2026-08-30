using TinyAgent.Reference;
using TinyAgent.Shared;

return await Cli.RunAsync(
    args,
    usage: """Usage: dotnet run --project ../TinyAgent.Reference -- "<your prompt>" """,
    makeTools: root => new ReferenceTools(root),
    run: (prompt, tools, client, onEvent) =>
        Agent.RunAsync(prompt, tools, client, onEvent: onEvent));
