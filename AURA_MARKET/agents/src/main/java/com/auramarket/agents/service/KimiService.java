package com.auramarket.agents.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import jakarta.annotation.PostConstruct;
import java.util.*;

@Service
public class KimiService {

    private final RestTemplate restTemplate;
    // IMPORTANT: host.docker.internal enables communication from container to host machine Ollama
    private final String OLLAMA_URL = "http://host.docker.internal:11434/api/chat";

    // Un seul modèle pour économiser la VRAM (RTX 3070 8GB)
    private final String MODEL_CHAT = "auramarket-agent";   // Changé pour auramarket-agent
    private final String MODEL_NEGO = "auramarket-agent";

    @Autowired
    private bridge.ErrorReporter errorReporter;



    public KimiService() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10000);
        factory.setReadTimeout(120000);  // 2min max
        this.restTemplate = new RestTemplate(factory);
    }

    @PostConstruct
    public void verifyModels() {
        checkModel(MODEL_CHAT,  "Modelfile-chat",  "ollama create auramarket-chat -f Modelfile-chat");
        checkModel(MODEL_NEGO,  "Modelfile",       "ollama create auramarket-agent -f Modelfile");
    }

    private void checkModel(String model, String file, String cmd) {
        try {
            ResponseEntity<String> r = restTemplate.getForEntity(
                "http://host.docker.internal:11434/api/tags", String.class);
            if (r.getBody() != null && !r.getBody().contains(model)) {
                System.err.println("════════════════════════════════════");
                System.err.println("[KimiService] MANQUANT : " + model);
                System.err.println("Lancer depuis resources/ : " + cmd);
                System.err.println("════════════════════════════════════");
            } else {
                System.out.println("[KimiService] ✓ " + model + " prêt.");
            }
        } catch (Exception e) {
            System.err.println("[KimiService] Ollama indisponible au démarrage.");
        }
    }

    /**
     * Sélectionne automatiquement le bon modèle selon le type.
     * CHAT/NAV → qwen3:8b (2-4s)
     * NEGO/AUTO/COMMENT → deepseek-r1 (8-12s)
     */
    private String selectModel(String type) {
        return MODEL_NEGO; // Utilise toujours auramarket-agent pour éviter de charger deux modèles en VRAM
    }

    /**
     * Task-specific methods with independent runtime prompts and timeouts.
     */
    public String detectNavigationIntent(String systemPrompt, String userMessage, List<Map<String, String>> history) {
        return askKimi(systemPrompt, userMessage, history, "NAV", 8000); // 8s timeout
    }

    public String generateManualNegotiationAdvice(String behavior, String trend) {
        String prompt = com.auramarket.agents.config.SystemPrompts.negoComment(behavior, trend);
        return askKimi(prompt, "Génère le commentaire.", null, "COMMENT", 15000); // 15s timeout
    }

    public String generateAutoNegotiationSummary(boolean accordTrouve, double prixFinal, String lastBuyerBehavior, String lastBuyerTrend) {
        String prompt = com.auramarket.agents.config.SystemPrompts.negoComment(lastBuyerBehavior, lastBuyerTrend);
        String promptDesc = accordTrouve
            ? String.format("Un accord a été trouvé à %.2f MAD ! Félicite l'acheteur.", prixFinal)
            : String.format("Aucun accord n'a été trouvé. La meilleure offre du vendeur était de %.2f MAD.", prixFinal);
        return askKimi(prompt, promptDesc, null, "COMMENT", 15000); // 15s timeout
    }

    public String generateChatResponse(String userMessage, String systemPrompt) {
        return askKimi(systemPrompt, userMessage, null, "CHAT", 8000); // 8s timeout
    }

    /**
     * Main callers mapping with default 2 min safety fallback timeout
     */
    public String askKimi(String systemPrompt, String userMessage) {
        return askKimi(systemPrompt, userMessage, null, "NEGO", 120000);
    }

    public String askKimi(String systemPrompt, String userMessage, List<Map<String, String>> history) {
        return askKimi(systemPrompt, userMessage, history, "NEGO", 120000);
    }

    public String askKimi(String systemPrompt, String userMessage, String type) {
        return askKimi(systemPrompt, userMessage, null, type, 120000);
    }

    public String askKimi(String systemPrompt, String userMessage, List<Map<String, String>> history, String type) {
        return askKimi(systemPrompt, userMessage, history, type, 120000);
    }

    public String askKimi(String systemPrompt, String userMessage,
                          List<Map<String, String>> history, String type, int timeoutMs) {

        String model = selectModel(type);
        long startTime = System.currentTimeMillis();
        String rawResponse = null;

        // Instantiation dynamically with custom explicit timeout requested
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(timeoutMs);
        factory.setReadTimeout(timeoutMs);
        RestTemplate localTemplate = new RestTemplate(factory);

        List<Map<String, String>> messages = new ArrayList<>();
        if (systemPrompt != null && !systemPrompt.isBlank()) {
            messages.add(Map.of("role", "system", "content", systemPrompt));
        }

        try {
            Map<String, Object> request = new HashMap<>();
            request.put("model", model);
            request.put("stream", false);
            request.put("keep_alive", "2m"); // Décharger après 2min d'inactivité
            request.put("options", Map.of(
                "temperature",    0.3,
                "num_predict",    512,
                "num_ctx",        4096,
                "repeat_penalty", 1.1
            ));

            // Historique (max 5 derniers échanges)
            if (history != null && !history.isEmpty()) {
                int start = Math.max(0, history.size() - 10);
                messages.addAll(history.subList(start, history.size()));
            }

            messages.add(Map.of("role", "user", "content", userMessage));
            request.put("messages", messages);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);

            ResponseEntity<Map> response = localTemplate.postForEntity(
                OLLAMA_URL, entity, Map.class);

            long duration = System.currentTimeMillis() - startTime;

            if (response.getStatusCode().is2xxSuccessful()
                    && response.getBody() != null) {

                Map<String, Object> body = response.getBody();
                Map<String, Object> msg  = (Map<String, Object>) body.get("message");

                if (msg != null) {
                    rawResponse = (String) msg.get("content");
                    String cleanedResponse = rawResponse;

                    // Supprimer le bloc <think> de deepseek-r1
                    if (cleanedResponse != null && cleanedResponse.contains("<think>")) {
                        cleanedResponse = cleanedResponse
                            .replaceAll("(?s)<think>.*?</think>", "")
                            .trim();
                    }

                    // Monitor trace
                    logToMonitorVerbose(type, model, userMessage, systemPrompt, 
                        rawResponse, cleanedResponse, duration, "ok", false, null);

                    System.out.println(String.format("[LlmService] SUCCESS | Model: %s | Prompt: %s | Duration: %dms | Status: OK | Fallback: NO", 
                        model, type, duration));

                    return cleanedResponse;
                }
            }

        } catch (Exception e) {
            long duration = System.currentTimeMillis() - startTime;
            String errMsg = "[LlmService] Erreur " + model + " après " + duration + "ms : " + e.getMessage();
            System.err.println(errMsg);
            
            if (errorReporter != null) {
                errorReporter.reportLLMError("LlmService", errMsg, e);
            }

            logToMonitorVerbose(type, model, userMessage, systemPrompt, 
                null, null, duration, "error", true, e.getMessage());
        }

        long duration = System.currentTimeMillis() - startTime;
        String fallbackVal = getFallbackResponse(userMessage, type);
        
        // Log Fallback execution
        logToMonitorVerbose(type, model, userMessage, systemPrompt, 
            null, fallbackVal, duration, "fallback", true, "Timeout or Inference Failure");

        System.out.println(String.format("[LlmService] FALLBACK | Model: %s | Prompt: %s | Duration: %dms | Status: TIMEOUT_ERROR | Fallback: YES", 
            model, type, duration));

        return fallbackVal;
    }

    private String getFallbackResponse(String userMessage, String type) {
        if (type == null) type = "CHAT";
        return switch (type.toUpperCase()) {
            case "NEGO"    -> "Je réfléchis à votre offre, un instant...";
            case "AUTO"    -> "{\"prixPropose\": 0, \"message\": \"Erreur calcul\"}";
            case "COMMENT" -> {
                if (userMessage != null && userMessage.contains("accord a été trouvé")) {
                    yield "Nous avons trouvé un accord !";
                } else if (userMessage != null && userMessage.contains("Aucun accord")) {
                    yield "Aucun accord n'a pu être trouvé dans votre budget.";
                } else {
                    yield "Le vendeur a fait une contre-proposition.";
                }
            }
            case "NAV", "CHAT" -> {
                String lower = userMessage != null ? userMessage.toLowerCase().trim() : "";
                
                // 1. Greeting words should not trigger search queries
                if (lower.matches("^(hello|hi|hey|bonjour|salut|allo|coucou|bonsoir|ciao|hola)$")) {
                    yield "{\"intention\":\"GENERAL\",\"recherche\":null,\"reponse\":\"Bonjour ! Comment puis-je vous aider aujourd'hui ?\"}";
                }
                
                // 2. Command keywords
                if (lower.contains("commande") || lower.contains("order")) {
                    yield "{\"intention\":\"CHECK_ORDER\",\"reponse\":" +
                          "\"Je vérifie vos commandes !\"}";
                }
                
                // 3. General Search
                yield "{\"intention\":\"SEARCH_PRODUCT\",\"recherche\":\"" +
                      userMessage + "\",\"reponse\":\"Je recherche pour vous !\"}";
            }
            default -> "Comment puis-je vous aider ?";
        };
    }

    private void logToMonitorVerbose(String type, String model,
                                      String userMessage, String systemPrompt,
                                      String rawResponse, String cleanedResponse,
                                      long duration, String status, 
                                      boolean fallbackUsed, String error) {
        java.util.concurrent.CompletableFuture.runAsync(() -> {
            try {
                Map<String, Object> payload = new HashMap<>();
                payload.put("promptType",      type != null ? type.toUpperCase() : "CHAT");
                payload.put("model",           model);
                payload.put("userMessage",     userMessage);
                payload.put("systemPrompt",    systemPrompt);
                payload.put("rawResponse",     rawResponse);
                payload.put("cleanedResponse", cleanedResponse);
                payload.put("duration",        duration);
                payload.put("status",          status);
                payload.put("fallbackUsed",    fallbackUsed);
                payload.put("error",           error);
                payload.put("time",            System.currentTimeMillis());

                HttpHeaders h = new HttpHeaders();
                h.setContentType(MediaType.APPLICATION_JSON);
                
                SimpleClientHttpRequestFactory f = new SimpleClientHttpRequestFactory();
                f.setConnectTimeout(1000);
                f.setReadTimeout(2000);
                
                new RestTemplate(f).postForEntity(
                    "http://host.docker.internal:9999/intercept",
                    new HttpEntity<>(payload, h), String.class);
            } catch (Exception ignored) {}
        });
    }
}
