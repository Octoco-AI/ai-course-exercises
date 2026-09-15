package ai.octoco.tinyagent.shared;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.ObjectMapper;

/** Shared Jackson configuration for the Gemini wire format. GIVEN. */
public final class GeminiJson {

    /** Null properties are omitted — the API rejects some explicit nulls. */
    public static final ObjectMapper MAPPER = new ObjectMapper()
            .setSerializationInclusion(JsonInclude.Include.NON_NULL);

    private GeminiJson() {}
}
