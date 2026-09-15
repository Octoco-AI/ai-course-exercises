package ai.octoco.tinyagent.shared;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;

/** A tool call requested by the model. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record FunctionCall(
        @JsonProperty("name") String name,
        @JsonProperty("args") JsonNode args) {
}
