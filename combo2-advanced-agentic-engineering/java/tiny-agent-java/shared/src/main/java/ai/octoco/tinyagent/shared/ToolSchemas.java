package ai.octoco.tinyagent.shared;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

/**
 * The JSON schemas the model sees for the three tools. GIVEN — you don't write these.
 *
 * <p><b>This file is where Java and Python genuinely diverge.</b> The Python SDK
 * reads your type hints and docstrings at runtime and generates this schema for
 * you, which makes for a lovely "look how little I wrote" moment. Java has no
 * runtime-readable docstrings, so the schema is written out by hand.
 *
 * <p>The trade is worth understanding rather than mourning: what the model
 * actually receives is <i>exactly this</i>, in both languages. Python hides it;
 * here you can read it. When a model calls a tool wrongly, this is the text you
 * need to look at — and in Python you would have had to go find it.
 *
 * <p>Descriptions are not decoration. They are the prompt for the tool.
 */
public final class ToolSchemas {

    public static final String READ_FILE = "read_file";
    public static final String LIST_FILES = "list_files";
    public static final String EDIT_FILE = "edit_file";

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private ToolSchemas() {}

    /** A single tools entry containing all three function declarations. */
    public static ObjectNode all() {
        ObjectNode tool = MAPPER.createObjectNode();
        ArrayNode declarations = tool.putArray("functionDeclarations");
        declarations.add(readFile());
        declarations.add(listFiles());
        declarations.add(editFile());
        return tool;
    }

    private static ObjectNode readFile() {
        ObjectNode props = MAPPER.createObjectNode();
        props.set("path", property("string",
                "File path relative to the working directory. Must not escape it "
                        + "(no absolute paths outside, no '..' traversal)."));

        return function(READ_FILE,
                "Read a file in the current working directory and return its contents as a string.",
                objectSchema(props, "path"));
    }

    private static ObjectNode listFiles() {
        ObjectNode props = MAPPER.createObjectNode();
        props.set("path", property("string",
                "Directory path relative to the working directory. Defaults to '.'."));

        return function(LIST_FILES,
                "List entries in a directory relative to the working directory. "
                        + "Directory names end with '/'.",
                objectSchema(props /* no required */));
    }

    private static ObjectNode editFile() {
        ObjectNode props = MAPPER.createObjectNode();
        props.set("path", property("string", "File path relative to the working directory."));
        props.set("old_str", property("string", "Exact text to find. Must appear exactly once in the file."));
        props.set("new_str", property("string", "Text to substitute in."));

        return function(EDIT_FILE,
                "Replace old_str with new_str in a file. old_str must appear exactly once. "
                        + "To change several places, call this once per place with enough surrounding "
                        + "context to make old_str unique.",
                objectSchema(props, "path", "old_str", "new_str"));
    }

    private static ObjectNode function(String name, String description, ObjectNode parameters) {
        ObjectNode fn = MAPPER.createObjectNode();
        fn.put("name", name);
        fn.put("description", description);
        fn.set("parameters", parameters);
        return fn;
    }

    private static ObjectNode property(String type, String description) {
        ObjectNode p = MAPPER.createObjectNode();
        p.put("type", type);
        p.put("description", description);
        return p;
    }

    private static ObjectNode objectSchema(ObjectNode properties, String... required) {
        ObjectNode schema = MAPPER.createObjectNode();
        schema.put("type", "object");
        schema.set("properties", properties);
        ArrayNode req = schema.putArray("required");
        for (String r : required) {
            req.add(r);
        }
        return schema;
    }
}
