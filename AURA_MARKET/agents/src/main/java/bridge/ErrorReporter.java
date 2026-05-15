package bridge;

import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class ErrorReporter {

    private final RestTemplate restTemplate = new RestTemplate();
    
    // Target address uses the inner Docker bridge DNS hostname
    private final String AUDIT_URL = "http://audit-service:8084/audits/errors";

    // Core atomic cache preventing database spam
    private final Map<String, Long> recentErrors = new ConcurrentHashMap<>();
    private static final long DEDUP_WINDOW_MS = 60000; // 1 Minute throttling

    @Async("errorReporterExecutor")
    public void report(String service, String errorType, String message, Exception ex) {
        reportFull(service, errorType, message, null, null, null, null, ex);
    }

    @Async("errorReporterExecutor")
    public void reportTimeout(String service, String agentName, long durationMs) {
        String msg = "Timeout: agent " + agentName + " took over " + durationMs + "ms";
        reportFull(service, "TIMEOUT", msg, null, null, null, agentName, null);
    }

    @Async("errorReporterExecutor")
    public void reportConfigError(String service, String message, String negoId, String prodId) {
        reportFull(service, "INVALID_CONFIG", message, negoId, null, prodId, null, null);
    }

    @Async("errorReporterExecutor")
    public void reportJadeError(String service, String message, Exception ex) {
        reportFull(service, "JADE_ERROR", message, null, null, null, null, ex);
    }

    @Async("errorReporterExecutor")
    public void reportLLMError(String service, String message, Exception ex) {
        reportFull(service, "LLM_ERROR", message, null, null, null, null, ex);
    }

    @Async("errorReporterExecutor")
    public void reportFull(String service, String errorType, String message,
                           String negociationId, String userId, String produitId,
                           String agentName, Exception ex) {
        
        String safeMessage = message != null ? message : "N/A";
        
        // 1. Deduplication logic
        String shortMsg = safeMessage.substring(0, Math.min(50, safeMessage.length()));
        String key = service + ":" + errorType + ":" + shortMsg;
        long now = System.currentTimeMillis();
        
        if (recentErrors.getOrDefault(key, 0L) > (now - DEDUP_WINDOW_MS)) {
            System.out.println("[ErrorReporter] Deduplication Active: Blocked redundant '" + key + "'");
            return;
        }
        recentErrors.put(key, now);

        // 2. Asynchronously build and transmit the DTO payload
        try {
            Map<String, Object> dto = new HashMap<>();
            dto.put("service", service);
            dto.put("errorType", errorType);
            dto.put("message", safeMessage);
            dto.put("negociationId", negociationId);
            dto.put("userId", userId);
            dto.put("produitId", produitId);
            dto.put("agentName", agentName);

            if (ex != null) {
                StringBuilder sb = new StringBuilder();
                sb.append(ex.toString()).append("\n");
                for (StackTraceElement el : ex.getStackTrace()) {
                    sb.append("  at ").append(el.toString()).append("\n");
                }
                dto.put("stackTrace", sb.toString());
            }

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(dto, headers);

            restTemplate.postForEntity(AUDIT_URL, entity, Map.class);
            System.out.println("[ErrorReporter] Emitter posted failure: " + key + " -> Status: SENT");
            
        } catch (Exception emitError) {
            // Fail silently locally to guarantee caller app stability
            System.err.println("[ErrorReporter FAIL] Critical emitter dispatch crash: " + emitError.getMessage());
        }
    }
}
