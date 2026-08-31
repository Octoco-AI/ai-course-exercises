namespace TinyAgent.Tests;

/// <summary>
/// Which implementation the tests exercise.
/// </summary>
/// <remarks>
/// <para>
/// <b>Defaults to your code</b> — both the tools and the loop. Set
/// <c>TINY_AGENT_IMPL=reference</c> to run the same suite against the worked
/// solution, useful to confirm the tests themselves are sane, or to see green
/// before you start.
/// </para>
/// <code>
/// dotnet test                                    # tests YOUR code
/// TINY_AGENT_IMPL=reference dotnet test          # tests the worked solution
/// </code>
/// <para>
/// The Python version of this exercise imports the reference implementation when
/// it is present and falls back to the starter, which means the suite goes green
/// against code the attendee never wrote until they hand-edit the import. This
/// is that bug fixed: here the default is always your own code.
/// </para>
/// </remarks>
internal static class Impl
{
    public static string Selected()
    {
        var impl = Environment.GetEnvironmentVariable("TINY_AGENT_IMPL")?.Trim().ToLowerInvariant();

        return impl switch
        {
            "reference" => "reference",
            "starter" or null or "" => "starter",
            _ => throw new InvalidOperationException(
                $"TINY_AGENT_IMPL must be 'starter' or 'reference', got '{impl}'."),
        };
    }
}
