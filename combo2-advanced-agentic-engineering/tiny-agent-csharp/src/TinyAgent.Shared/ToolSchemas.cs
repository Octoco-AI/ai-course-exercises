using System.Text.Json.Nodes;

namespace TinyAgent.Shared;

/// <summary>
/// The JSON schemas the model sees for the three tools. GIVEN — you don't write these.
/// </summary>
/// <remarks>
/// <para>
/// <b>This file is where C# and Python genuinely diverge.</b> The Python SDK
/// reads your type hints and docstrings at runtime and generates this schema for
/// you, which makes for a lovely "look how little I wrote" moment. C# has no
/// runtime-readable docstrings, so the schema is written out by hand.
/// </para>
/// <para>
/// The trade is worth understanding rather than mourning: what the model
/// actually receives is <i>exactly this</i>, in both languages. Python hides it;
/// here you can read it. When a model calls a tool wrongly, this is the text you
/// need to look at — and in Python you would have had to go find it.
/// </para>
/// <para>
/// Descriptions are not decoration. They are the prompt for the tool.
/// </para>
/// </remarks>
public static class ToolSchemas
{
    public const string ReadFileName = "read_file";
    public const string ListFilesName = "list_files";
    public const string EditFileName = "edit_file";

    public static ToolDeclaration All() => new(new[]
    {
        new FunctionDeclaration(
            ReadFileName,
            "Read a file in the current working directory and return its contents as a string.",
            Object(
                properties: new()
                {
                    ["path"] = Property("string",
                        "File path relative to the working directory. Must not escape it "
                        + "(no absolute paths outside, no '..' traversal)."),
                },
                required: new[] { "path" })),

        new FunctionDeclaration(
            ListFilesName,
            "List entries in a directory relative to the working directory. "
            + "Directory names end with '/'.",
            Object(
                properties: new()
                {
                    ["path"] = Property("string",
                        "Directory path relative to the working directory. Defaults to '.'."),
                },
                required: Array.Empty<string>())),

        new FunctionDeclaration(
            EditFileName,
            "Replace old_str with new_str in a file. old_str must appear exactly once. "
            + "To change several places, call this once per place with enough surrounding "
            + "context to make old_str unique.",
            Object(
                properties: new()
                {
                    ["path"] = Property("string", "File path relative to the working directory."),
                    ["old_str"] = Property("string", "Exact text to find. Must appear exactly once in the file."),
                    ["new_str"] = Property("string", "Text to substitute in."),
                },
                required: new[] { "path", "old_str", "new_str" })),
    });

    private static JsonObject Property(string type, string description) =>
        new() { ["type"] = type, ["description"] = description };

    private static JsonObject Object(Dictionary<string, JsonObject> properties, IReadOnlyList<string> required)
    {
        var props = new JsonObject();
        foreach (var (key, value) in properties) props[key] = value;

        return new JsonObject
        {
            ["type"] = "object",
            ["properties"] = props,
            ["required"] = new JsonArray(required.Select(r => (JsonNode)r!).ToArray()),
        };
    }
}
