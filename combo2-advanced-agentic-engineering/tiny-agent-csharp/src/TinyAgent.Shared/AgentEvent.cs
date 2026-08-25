namespace TinyAgent.Shared;

/// <summary>
/// What the agent loop reports as it runs. GIVEN — you don't write this.
/// </summary>
/// <remarks>
/// The observer hook exists so later modules have somewhere to attach: M12
/// (CI/CD/CE) traces from here, and M16 (context engineering) counts tokens
/// from here. Keep calling <c>onEvent</c> from your loop even when nothing is
/// listening.
/// </remarks>
public abstract record AgentEvent
{
    public sealed record TurnStart(int Turn) : AgentEvent;
    public sealed record ToolCall(string Name, string ArgsPreview) : AgentEvent;
    public sealed record ToolResult(string Name, string Result) : AgentEvent;
    public sealed record Final(string Text, int Turns) : AgentEvent;
}
