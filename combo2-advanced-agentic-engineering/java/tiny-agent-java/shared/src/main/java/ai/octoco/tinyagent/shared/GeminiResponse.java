package ai.octoco.tinyagent.shared;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/** The model's reply. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record GeminiResponse(
        @JsonProperty("candidates") List<Candidate> candidates,
        @JsonProperty("promptFeedback") Object promptFeedback) {

    public Candidate firstCandidate() {
        return candidates == null || candidates.isEmpty() ? null : candidates.get(0);
    }
}
