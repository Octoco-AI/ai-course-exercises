package ai.octoco.tinyagent.shared;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;

/**
 * The Gemini REST wire format, as records spread across this package. This is
 * the whole API surface the agent needs — a handful of small types and no SDK.
 *
 * <p>Read {@link Content} and {@link Part} once and the shape of every
 * function-calling API stops being mysterious: a list of turns, each turn a
 * list of parts, each part either text or a function call. Anthropic and
 * OpenAI differ in names, not in shape.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record GeminiRequest(
        @JsonProperty("contents") List<Content> contents,
        @JsonProperty("tools") List<JsonNode> tools,
        @JsonProperty("systemInstruction") Content systemInstruction) {
}
