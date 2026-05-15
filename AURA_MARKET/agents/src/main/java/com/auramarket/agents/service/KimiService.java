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

    // Deux modèles spécialisés
    private final String MODEL_CHAT = "auramarket-chat";   // qwen3:8b — rapide
    private final String MODEL_NEGO = "auramarket-agent";  // deepseek-r1 — précis

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
        if (type == null) return MODEL_CHAT;
        return switch (type.toUpperCase()) {
            case "CHAT", "NAV", "NAVIGATION" -> MODEL_CHAT;
            default -> MODEL_NEGO;
        };
    }

    /**
     * Appel principal — sélection automatique du modèle
     */
    public String askKimi(String systemPrompt, String userMessage) {
        return askKimi(systemPrompt, userMessage, null, "NEGO");
    }

    public String askKimi(String systemPrompt, String userMessage,
                          List<Map<String, String>> history) {
        return askKimi(systemPrompt, userMessage, history, "NEGO");
    }

    public String askKimi(String systemPrompt, String userMessage,
                          String type) {
        return askKimi(systemPrompt, userMessage, null, type);
    }

    public String askKimi(String systemPrompt, String userMessage,
                          List<Map<String, String>> history, String type) {

        String model = selectModel(type);
        long startTime = System.currentTimeMillis();

        try {
            Map<String, Object> request = new HashMap<>();
            request.put("model", model);
            request.put("stream", false);
            request.put("options", Map.of(
                "temperature",    model.equals(MODEL_CHAT) ? 0.2 : 0.3,
                "num_predict",    model.equals(MODEL_CHAT) ? 256  : 512,
                "num_ctx",        model.equals(MODEL_CHAT) ? 2048 : 4096,
                "repeat_penalty", 1.1
            ));

            List<Map<String, String>> messages = new ArrayList<>();
            if (systemPrompt != null && !systemPrompt.isBlank()) {
                messages.add(Map.of("role", "system", "content", systemPrompt));
            }

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

            ResponseEntity<Map> response = restTemplate.postForEntity(
                OLLAMA_URL, entity, Map.class);

            long duration = System.currentTimeMillis() - startTime;

            if (response.getStatusCode().is2xxSuccessful()
                    && response.getBody() != null) {

                Map<String, Object> body = response.getBody();
                Map<String, Object> msg  = (Map<String, Object>) body.get("message");

                if (msg != null) {
                    String content = (String) msg.get("content");

                    // Supprimer le bloc <think> de deepseek-r1
                    if (content != null && content.contains("<think>")) {
                        content = content
                            .replaceAll("(?s)<think>.*?</think>", "")
                            .trim();
                    }

                    // Logger vers monitor
                    logToMonitor(type, "KimiService → " + model,
                        messages, null, content, duration, "ok", null);

                    System.out.println("[KimiService] " + model
                        + " → " + duration + "ms | type=" + type);

                    return content;
                }
            }

        } catch (Exception e) {
            long duration = System.currentTimeMillis() - startTime;
            String errMsg = "[KimiService] Erreur " + model + " après " + duration + "ms : " + e.getMessage();
            System.err.println(errMsg);
            
            if (errorReporter != null) {
                errorReporter.reportLLMError("KimiService", errMsg, e);
            }

            logToMonitor(type, "KimiService → ERROR",
                null, null, null, duration, "error", e.getMessage());
        }

        return getFallbackResponse(userMessage, type);
    }

    private String getFallbackResponse(String userMessage, String type) {
        if (type == null) type = "CHAT";
        return switch (type.toUpperCase()) {
            case "NEGO"    -> "Je réfléchis à votre offre, un instant...";
            case "AUTO"    -> "{\"prixPropose\": 0, \"message\": \"Erreur calcul\"}";
            case "COMMENT" -> "Le vendeur a fait une contre-proposition.";
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

    private void logToMonitor(String type, String source,
                               List<?> messages, String think,
                               String response, long duration,
                               String status, String error) {
        java.util.concurrent.CompletableFuture.runAsync(() -> {
            try {
                Map<String, Object> payload = new HashMap<>();
                payload.put("type",     type != null ? type.toUpperCase() : "CHAT");
                payload.put("source",   source);
                payload.put("messages", messages);
                payload.put("think",    think);
                payload.put("response", response);
                payload.put("duration", duration);
                payload.put("status",   status);
                payload.put("error",    error);
                payload.put("time",     System.currentTimeMillis());

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
