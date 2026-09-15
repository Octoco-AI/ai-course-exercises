package ai.octoco.tinyagent.shared;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/** One turn: a role ("user" or "model") and the parts that make it up. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record Content(
        @JsonProperty("role") String role,
        @JsonProperty("parts") List<Part> parts) {
}
