package ai.octoco.tinyagent.shared;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** One candidate reply from the model. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record Candidate(
        @JsonProperty("content") Content content,
        @JsonProperty("finishReason") String finishReason) {
}
