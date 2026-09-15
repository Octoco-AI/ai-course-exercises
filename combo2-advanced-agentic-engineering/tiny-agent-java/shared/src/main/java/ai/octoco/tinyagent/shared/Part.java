package ai.octoco.tinyagent.shared;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * One piece of a turn. Exactly one of the three properties is set.
 *
 * <p>A part is text, OR a function call from the model, OR a function response
 * from you. Checking for null on the wrong one is the Java equivalent of the
 * Python original's "parts have .text XOR .function_call" footgun.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record Part(
        @JsonProperty("text") String text,
        @JsonProperty("functionCall") FunctionCall functionCall,
        @JsonProperty("functionResponse") FunctionResponse functionResponse) {

    public static Part text(String text) {
        return new Part(text, null, null);
    }

    public static Part functionResponse(FunctionResponse response) {
        return new Part(null, null, response);
    }
}
