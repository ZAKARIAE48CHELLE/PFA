package agents;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import jade.core.Agent;
import jade.core.behaviours.CyclicBehaviour;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.List;

/**
 * Agent JADE responsable de la vérification de sécurité via ML API.
 */
public class AgentSecurite extends Agent {

    private static final ObjectMapper mapper = new ObjectMapper();
    private final RestTemplate restTemplate = new RestTemplate();
    private String mlApiUrl = "http://localhost:5000";

    @Override
    protected void setup() {
        Object[] args = getArguments();
        if (args != null && args.length > 0 && args[0] != null) {
            mlApiUrl = String.valueOf(args[0]);
        }
        System.out.println("[AgentSecurite] Agent démarré : " + getLocalName());
        System.out.println("[AgentSecurite] ML API URL : " + mlApiUrl);

        addBehaviour(new CyclicBehaviour() {
            @Override
            public void action() {
                ACLMessage msg = receive(MessageTemplate.MatchPerformative(ACLMessage.REQUEST));
                if (msg != null) {
                    try {
                        JsonNode req = mapper.readTree(msg.getContent());
                        String type = req.has("type") ? req.get("type").asText() : "OFFRE";

                        ObjectNode response;
                        if ("OFFRE".equalsIgnoreCase(type)) {
                            response = analyserOffre(req);
                        } else if ("COMMENTAIRE".equalsIgnoreCase(type)) {
                            response = verifierCommentaire(req);
                        } else {
                            response = mapper.createObjectNode();
                            response.put("statut", "ERREUR");
                            response.put("raison", "Type inconnu : " + type);
                        }

                        // if old format, retain offreId
                        if (req.has("offreId")) {
                            response.put("offreId", req.get("offreId").asText());
                        }

                        ACLMessage reply = msg.createReply();
                        reply.setPerformative(ACLMessage.INFORM);
                        reply.setContent(mapper.writeValueAsString(response));
                        send(reply);

                    } catch (Exception e) {
                        ACLMessage reply = msg.createReply();
                        reply.setPerformative(ACLMessage.FAILURE);
                        reply.setContent("{\"error\": \"" + e.getMessage().replace("\"", "'") + "\"}");
                        send(reply);
                        System.err.println("[AgentSecurite] Erreur : " + e.getMessage());
                    }
                } else {
                    block();
                }
            }
        });
    }

    private ObjectNode analyserOffre(JsonNode req) {
        try {
            double prix = req.has("prix") ? req.get("prix").asDouble() : (req.has("prixOffre") ? req.get("prixOffre").asDouble() : 0.0);
            double prixBase = req.has("prixBase") ? req.get("prixBase").asDouble() : (req.has("prixProduit") ? req.get("prixProduit").asDouble() : 0.0);
            String categorie = req.path("categorie").asText("accessoire");
            double rating = req.path("rating").asDouble(3.0);

            ObjectNode payload = mapper.createObjectNode();
            payload.put("price", prix);
            payload.put("base_price", prixBase);
            payload.put("category", categorie);
            payload.put("rating", rating);

            JsonNode mlResponse = postJson("/detect/offer", payload);

            ObjectNode response = mapper.createObjectNode();
            String statutMl = mlResponse.path("statut").asText("ACCEPTABLE");
            
            boolean isSuspect = "NON ACCEPTABLE".equalsIgnoreCase(statutMl);
            response.put("statut", isSuspect ? "SUSPECT" : "ACCEPTABLE");
            response.put("isSuspect", isSuspect);
            
            double scoreFraude = mlResponse.path("score_fraude").asDouble(0.0);
            response.put("scoreConfiance", Math.round((1.0 - scoreFraude) * 100.0) / 100.0);

            if (isSuspect) {
                StringBuilder raisons = new StringBuilder();
                if (mlResponse.has("raisons") && mlResponse.get("raisons").isArray()) {
                    for (JsonNode r : mlResponse.get("raisons")) {
                        if (raisons.length() > 0) raisons.append(" | ");
                        raisons.append(r.asText());
                    }
                }
                if (raisons.length() == 0) raisons.append(mlResponse.path("message").asText("Offre jugée incohérente"));
                
                response.put("raison", raisons.toString());

                ArrayNode alternatives = mapper.createArrayNode();
                if (mlResponse.has("propositions") && mlResponse.get("propositions").isArray()) {
                    for (JsonNode prop : mlResponse.get("propositions")) {
                        double percent = prop.asDouble();
                        double altPrix = Math.round(prixBase * (1 - percent / 100.0) * 100.0) / 100.0;
                        alternatives.add(altPrix);
                    }
                }
                response.set("alternatives", alternatives);
            } else {
                response.put("raison", mlResponse.path("message").asText("Offre acceptable"));
                response.set("alternatives", mapper.createArrayNode());
            }

            return response;

        } catch (Exception e) {
            System.err.println("[AgentSecurite] Erreur ML Offre : " + e.getMessage());
            return fallbackAnalyserOffre(req);
        }
    }

    private ObjectNode fallbackAnalyserOffre(JsonNode req) {
        double prix = req.has("prix") ? req.get("prix").asDouble() : (req.has("prixOffre") ? req.get("prixOffre").asDouble() : 0.0);
        double prixBase = req.has("prixBase") ? req.get("prixBase").asDouble() : (req.has("prixProduit") ? req.get("prixProduit").asDouble() : 0.0);

        List<String> raisons = new ArrayList<>();
        if (prix <= 0) raisons.add("Prix négatif ou zéro");
        if (prix > 2 * prixBase) raisons.add("Prix supérieur à 2x le prix de base");
        if (prix < 0.10 * prixBase) raisons.add("Prix inférieur à 10% du prix de base");

        ObjectNode response = mapper.createObjectNode();
        boolean suspect = !raisons.isEmpty();
        response.put("statut", suspect ? "SUSPECT" : "ACCEPTABLE");
        response.put("isSuspect", suspect);
        response.put("scoreConfiance", suspect ? 0.7 : 0.95);
        response.put("raison", suspect ? String.join(" | ", raisons) : "Prix dans les limites acceptables (fallback)");
        
        ArrayNode alternatives = mapper.createArrayNode();
        if (suspect) {
            alternatives.add(Math.round(prixBase * 0.85 * 100.0) / 100.0);
            alternatives.add(Math.round(prixBase * 0.75 * 100.0) / 100.0);
            alternatives.add(Math.round(prixBase * 0.60 * 100.0) / 100.0);
        }
        response.set("alternatives", alternatives);
        return response;
    }

    private ObjectNode verifierCommentaire(JsonNode node) {
        String texte = node.path("texte").asText(node.path("commentaire").asText(""));
        int note = node.path("note").asInt(3);

        try {
            ObjectNode payloadNew = mapper.createObjectNode();
            payloadNew.put("text", texte);
            payloadNew.put("note", note);
            JsonNode mlResponse = postJson("/detect/comment", payloadNew);
            return mapCommentResponse(mlResponse);
        } catch (Exception ignored) {
            try {
                ObjectNode payloadLegacy = mapper.createObjectNode();
                payloadLegacy.put("texte", texte);
                payloadLegacy.put("note", note);
                payloadLegacy.put("noteMoyenne", 3.0);
                JsonNode legacyResponse = postJson("/detect/fake-comment", payloadLegacy);
                ObjectNode mapped = mapper.createObjectNode();
                mapped.put("statut", legacyResponse.path("statut").asText("AUTHENTIQUE"));
                mapped.put("scoreConfiance", legacyResponse.path("scoreConfiance").asDouble(0.0));
                mapped.put("scoreSuspicion", legacyResponse.path("scoreSuspicion").asInt(0));
                ArrayNode raisonsDetectees = mapper.createArrayNode();
                if (legacyResponse.has("raisonsDetectees") && legacyResponse.get("raisonsDetectees").isArray()) {
                    for (JsonNode raison : legacyResponse.get("raisonsDetectees")) {
                        raisonsDetectees.add(raison.asText());
                    }
                }
                mapped.set("raisonsDetectees", raisonsDetectees);
                return mapped;
            } catch (Exception ex) {
                return buildMlUnavailableResponse();
            }
        }
    }

    private ObjectNode mapCommentResponse(JsonNode mlResponse) {
        ObjectNode response = mapper.createObjectNode();
        response.put("statut", mlResponse.path("statut").asText("AUTHENTIQUE"));
        response.put("scoreConfiance", mlResponse.path("confiance").asDouble(0.0));
        response.put("scoreSuspicion", (int) Math.round(mlResponse.path("score_fake").asDouble(0.0) * 100.0));

        ArrayNode raisonsDetectees = mapper.createArrayNode();
        if (mlResponse.has("raisons") && mlResponse.get("raisons").isArray()) {
            for (JsonNode raison : mlResponse.get("raisons")) {
                raisonsDetectees.add(raison.asText());
            }
        }
        response.set("raisonsDetectees", raisonsDetectees);
        return response;
    }

    private ObjectNode buildMlUnavailableResponse() {
            ObjectNode fallback = mapper.createObjectNode();
            fallback.put("statut", "ERREUR");
            fallback.put("scoreConfiance", 0.0);
            fallback.put("scoreSuspicion", 0);
            ArrayNode raisons = mapper.createArrayNode();
            raisons.add("ML service unavailable");
            fallback.set("raisonsDetectees", raisons);
            return fallback;
    }

    private JsonNode postJson(String endpoint, JsonNode payload) throws Exception {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<String> entity = new HttpEntity<>(mapper.writeValueAsString(payload), headers);
        String responseBody = restTemplate.postForObject(mlApiUrl + endpoint, entity, String.class);
        if (responseBody == null || responseBody.isBlank()) {
            throw new RuntimeException("Réponse vide du service ML: " + endpoint);
        }
        return mapper.readTree(responseBody);
    }

    @Override
    protected void takeDown() {
        System.out.println("[AgentSecurite] Agent arrêté : " + getLocalName());
    }
}
