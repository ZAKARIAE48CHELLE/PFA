package com.auramarket.agents.service;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import java.util.*;

@Service
public class KimiService {

    private final RestTemplate restTemplate;
    private final RestTemplate monitorRestTemplate;
    private final String OLLAMA_URL = "http://host.docker.internal:11434/api/chat";
    private final String MODEL = "deepseek-r1:14b";

    public KimiService() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(120000);
        this.restTemplate = new RestTemplate(factory);

        SimpleClientHttpRequestFactory monitorFactory = new SimpleClientHttpRequestFactory();
        monitorFactory.setConnectTimeout(1000);
        monitorFactory.setReadTimeout(2000); // 2s max for monitor
        this.monitorRestTemplate = new RestTemplate(monitorFactory);
    }

    public String askKimi(String systemPrompt, String userMessage, String type) {
        return askKimi(systemPrompt, userMessage, new ArrayList<>(), type);
    }

    public String askKimi(String systemPrompt, String userMessage, List<Map<String, String>> history, String type) {
        long startTime = System.currentTimeMillis();
        List<Map<String, String>> messages = new ArrayList<>();
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("model", MODEL);
            request.put("stream", false);
            
            Map<String, Object> options = new HashMap<>();
            options.put("num_predict", 2048);
            options.put("temperature", 0.1);
            options.put("top_p", 0.9);
            request.put("options", options);

            messages.add(Map.of("role", "system", "content", systemPrompt));
            if (history != null) {
                int start = Math.max(0, history.size() - 10);
                messages.addAll(history.subList(start, history.size()));
            }
            messages.add(Map.of("role", "user", "content", userMessage));
            request.put("messages", messages);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(request, headers);
            ResponseEntity<Map> response = restTemplate.postForEntity(OLLAMA_URL, entity, Map.class);

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                Map<String, Object> body = response.getBody();
                Map<String, Object> message = (Map<String, Object>) body.get("message");
                if (message != null) {
                    String rawContent = (String) message.get("content");
                    long duration = System.currentTimeMillis() - startTime;
                    
                    String think = extractThink(rawContent);
                    String clean = (rawContent != null) ? rawContent.replaceAll("(?si)<think>.*?(</think>|$)", "").trim() : "";
                    
                    logToMonitor(type != null ? type : detectType(systemPrompt), "KimiService → Ollama", 
                                 messages, think, clean, duration, 0, "ok", null);
                    
                    return clean;
                }
            }
        } catch (Exception e) {
            long duration = System.currentTimeMillis() - startTime;
            System.err.println("[KimiService] Error calling Ollama: " + e.getMessage());
            logToMonitor(type != null ? type : "ERROR", "KimiService → timeout/failure", 
                         messages, null, null, duration, 0, "error", e.getMessage());
        }
        return getFallbackResponse(userMessage, type);
    }

    private String getFallbackResponse(String userMessage, String type) {
        if ("NEGO".equals(type) || "AUTO".equals(type)) {
            return "Je réfléchis à votre offre, un instant...";
        }
        if ("COMMENT".equals(type)) {
            return "Le vendeur a fait une contre-proposition.";
        }
        
        // fallback chat navigation existant
        String lower = userMessage.toLowerCase();
        if (lower.contains("négocier") || lower.contains("prix")) {
            return "Je peux vous aider à trouver le meilleur prix !";
        } else if (lower.contains("commande") || lower.contains("statut")) {
            return "Je peux vérifier le statut de votre commande. Pourriez-vous me donner plus de détails ?";
        } else if (lower.contains("produit") || lower.contains("cherche")) {
            return "Nous avons une large sélection de produits. Quelle catégorie vous intéresse ?";
        }
        return "Comment puis-je vous aider sur AuraMarket ?";
    }

    private void logToMonitor(String type, String source,
                               List<Map<String,String>> messages,
                               String think, String response,
                               long duration, int tokens, String status, String error) {
        java.util.concurrent.CompletableFuture.runAsync(() -> {
            try {
                Map<String, Object> payload = new HashMap<>();
                payload.put("type",      type);
                payload.put("source",    source);
                payload.put("messages",  messages);
                payload.put("think",     think);
                payload.put("response",  response);
                payload.put("duration",  duration);
                payload.put("tokens",    tokens);
                payload.put("status",    status);
                payload.put("error",     error);
                payload.put("time",      System.currentTimeMillis());

                HttpHeaders h = new HttpHeaders();
                h.setContentType(MediaType.APPLICATION_JSON);
                
                // Use host.docker.internal to reach monitor outside container
                monitorRestTemplate.postForEntity(
                    "http://host.docker.internal:9999/intercept",
                    new HttpEntity<>(payload, h),
                    String.class
                );
            } catch (Exception ignored) {
                // Monitor hors ligne — ne pas crasher
            }
        });
    }

    private String detectType(String systemPrompt) {
        if (systemPrompt == null) return "CHAT";
        String s = systemPrompt.toLowerCase();
        if (s.contains("négociateur") || s.contains("nego_auto")) return "AUTO";
        if (s.contains("vendeur") || s.contains("contre-proposition")) return "NEGO";
        if (s.contains("navigation") || s.contains("intention")) return "NAV";
        return "CHAT";
    }

    private String extractThink(String content) {
        if (content == null) return null;
        java.util.regex.Pattern p = java.util.regex.Pattern.compile("(?si)<think>(.*?)(</think>|$)");
        java.util.regex.Matcher m = p.matcher(content);
        if (m.find()) return m.group(1).trim();
        return null;
    }
}
