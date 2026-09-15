package ai.octoco.tinyagent.shared;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;

/** A tool's result, sent back to the model. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record FunctionResponse(
        @JsonProperty("name") String name,
        @JsonProperty("response") JsonNode response) {
}
