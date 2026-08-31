using TinyAgent.Shared;

namespace TinyAgent.Tests;

/// <summary>
/// The tool implementation under test. See <see cref="Impl"/> for the switch.
/// </summary>
public static class ToolsFactory
{
    public static ITools Create(string sandboxRoot) =>
        Impl.Selected() == "reference"
            ? new Reference.ReferenceTools(sandboxRoot)
            : new Starter.StarterTools(sandboxRoot);

    public static string Describe() =>
        Impl.Selected() == "reference"
            ? "reference (worked solution)"
            : "starter (your code)";
}
