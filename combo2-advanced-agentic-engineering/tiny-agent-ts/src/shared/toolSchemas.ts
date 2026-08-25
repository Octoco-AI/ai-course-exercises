import { Type, type FunctionDeclaration } from "@google/genai";

/**
 * The JSON schemas the model sees for the three tools. GIVEN — you don't write these.
 *
 * **This is where TypeScript and Python genuinely diverge.** The Gemini Python
 * SDK reads type hints and docstrings at runtime and generates this schema for
 * you, which makes for a lovely "look how little I wrote" moment. TypeScript
 * erases its types at compile time, so there is nothing to introspect at runtime
 * and the schema is written out by hand.
 *
 * The trade is worth understanding rather than mourning: what the model actually
 * receives is *exactly this*, in both languages. Python hides it; here you can
 * read it. When a model calls a tool wrongly, this is the text you need to look
 * at — and in Python you would have had to go find it.
 *
 * Descriptions are not decoration. They are the prompt for the tool.
 */
export const READ_FILE = "read_file";
export const LIST_FILES = "list_files";
export const EDIT_FILE = "edit_file";

export const TOOL_DECLARATIONS: FunctionDeclaration[] = [
  {
    name: READ_FILE,
    description:
      "Read a file in the current working directory and return its contents as a string.",
    parameters: {
      type: Type.OBJECT,
      properties: {
        path: {
          type: Type.STRING,
          description:
            "File path relative to the working directory. Must not escape it " +
            "(no absolute paths outside, no '..' traversal).",
        },
      },
      required: ["path"],
    },
  },
  {
    name: LIST_FILES,
    description:
      "List entries in a directory relative to the working directory. " +
      "Directory names end with '/'.",
    parameters: {
      type: Type.OBJECT,
      properties: {
        path: {
          type: Type.STRING,
          description: "Directory path relative to the working directory. Defaults to '.'.",
        },
      },
      required: [],
    },
  },
  {
    name: EDIT_FILE,
    description:
      "Replace old_str with new_str in a file. old_str must appear exactly once. " +
      "To change several places, call this once per place with enough surrounding " +
      "context to make old_str unique.",
    parameters: {
      type: Type.OBJECT,
      properties: {
        path: {
          type: Type.STRING,
          description: "File path relative to the working directory.",
        },
        old_str: {
          type: Type.STRING,
          description: "Exact text to find. Must appear exactly once in the file.",
        },
        new_str: {
          type: Type.STRING,
          description: "Text to substitute in.",
        },
      },
      required: ["path", "old_str", "new_str"],
    },
  },
];

/** The system prompt. Identical to the Python path, word for word. */
export const SYSTEM_INSTRUCTION = `You are a careful coding assistant working inside a small
code repository. You have three tools: read_file, list_files, and edit_file.

Workflow:
1. Explore first. Use list_files and read_file to build an understanding before editing.
2. Edit sparingly. One edit per logical change. Use enough surrounding context in
   old_str so it matches exactly once.
3. Report what you did in plain prose when you are finished. Do not call any tool on
   the final turn — that's how you signal you're done.
4. If a tool returns a string starting with "ERROR:", read the error carefully and
   adjust your approach. Don't retry the same call blindly.
`;

export const DEFAULT_MODEL = "gemini-3.1-flash-lite";

/** The model id from the environment, or the workshop default. */
export function resolveModel(): string {
  return process.env["GEMINI_MODEL"] || DEFAULT_MODEL;
}
