using TinyAgent.Shared;
using Xunit;

namespace TinyAgent.Tests;

/// <summary>
/// The contract your tool implementations must satisfy.
/// </summary>
/// <remarks>
/// These 13 tests ARE the spec — read them before you write anything. They are
/// also a preview of M11: notice that each one names a behaviour and asserts on
/// it, rather than checking the implementation.
///
/// Run from the tiny-agent-csharp/ directory:
///     dotnet test
/// </remarks>
public sealed class ToolsTests : IDisposable
{
    private readonly string _sandbox;
    private readonly ITools _tools;

    public ToolsTests()
    {
        // A fresh temp directory per test, seeded the same way as the Python
        // fixture: one file, one nested directory with a file in it.
        _sandbox = Path.Combine(Path.GetTempPath(), "tiny-agent-tests-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_sandbox);

        File.WriteAllText(Path.Combine(_sandbox, "hello.txt"), "hello world\n");
        Directory.CreateDirectory(Path.Combine(_sandbox, "nested"));
        File.WriteAllText(Path.Combine(_sandbox, "nested", "deep.txt"), "deep content\n");

        _tools = ToolsFactory.Create(_sandbox);
    }

    public void Dispose()
    {
        if (Directory.Exists(_sandbox)) Directory.Delete(_sandbox, recursive: true);
    }

    private string Read(string relative) => File.ReadAllText(Path.Combine(_sandbox, relative));

    // ---- ReadFile -----------------------------------------------------------

    [Fact]
    public void ReadFile_Success()
    {
        Assert.Equal("hello world\n", _tools.ReadFile("hello.txt"));
    }

    [Fact]
    public void ReadFile_Nested()
    {
        Assert.Equal("deep content\n", _tools.ReadFile("nested/deep.txt"));
    }

    [Fact]
    public void ReadFile_Missing()
    {
        var result = _tools.ReadFile("does-not-exist.txt");
        Assert.StartsWith("ERROR:", result);
        Assert.Contains("does not exist", result);
    }

    [Fact]
    public void ReadFile_DirectoryNotFile()
    {
        var result = _tools.ReadFile("nested");
        Assert.StartsWith("ERROR:", result);
        Assert.Contains("not a file", result);
    }

    [Fact]
    public void ReadFile_EscapeAttempt()
    {
        // The guard. If this ever goes green by accident, the sandbox is broken.
        var result = _tools.ReadFile("../outside.txt");
        Assert.StartsWith("ERROR:", result);
        Assert.Contains("outside", result);
    }

    // ---- ListFiles ----------------------------------------------------------

    [Fact]
    public void ListFiles_Root()
    {
        var result = _tools.ListFiles(".");
        Assert.False(result.IsError);
        Assert.Contains("hello.txt", result.Entries!);
        Assert.Contains("nested/", result.Entries!);
    }

    [Fact]
    public void ListFiles_Nested()
    {
        var result = _tools.ListFiles("nested");
        Assert.False(result.IsError);
        Assert.Equal(new[] { "deep.txt" }, result.Entries!);
    }

    [Fact]
    public void ListFiles_Missing()
    {
        var result = _tools.ListFiles("no-such-dir");
        Assert.True(result.IsError);
        Assert.StartsWith("ERROR:", result.Error!);
    }

    [Fact]
    public void ListFiles_OnFile()
    {
        var result = _tools.ListFiles("hello.txt");
        Assert.True(result.IsError);
        Assert.StartsWith("ERROR:", result.Error!);
    }

    // ---- EditFile -----------------------------------------------------------

    [Fact]
    public void EditFile_Success()
    {
        var result = _tools.EditFile("hello.txt", "hello", "hi");
        Assert.StartsWith("OK:", result);
        Assert.Equal("hi world\n", Read("hello.txt"));
    }

    [Fact]
    public void EditFile_MissingOldStr()
    {
        var result = _tools.EditFile("hello.txt", "goodbye", "hi");
        Assert.StartsWith("ERROR:", result);
        Assert.Contains("not found", result);
    }

    [Fact]
    public void EditFile_NonUniqueOldStr()
    {
        File.WriteAllText(Path.Combine(_sandbox, "repeated.txt"), "foo bar foo baz\n");

        var result = _tools.EditFile("repeated.txt", "foo", "qux");
        Assert.StartsWith("ERROR:", result);
        Assert.Contains("2 times", result);

        // The file must NOT have been modified on a non-unique match. This is the
        // test that catches a naive string.Replace().
        Assert.Equal("foo bar foo baz\n", Read("repeated.txt"));
    }

    [Fact]
    public void EditFile_PreservesFileOnError()
    {
        var original = Read("hello.txt");
        _tools.EditFile("hello.txt", "nope", "yep");
        Assert.Equal(original, Read("hello.txt"));
    }
}
