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

/**
 * Agent JADE responsable de la génération d'offres de prix via ML API.
 */
public class AgentOffre extends Agent {

    private static final ObjectMapper mapper = new ObjectMapper();
    private String mlApiUrl = "http://localhost:5000";
    private final RestTemplate restTemplate = new RestTemplate();

    @Override
    protected void setup() {
        Object[] args = getArguments();
        if (args != null && args.length > 0 && args[0] != null) {
            mlApiUrl = String.valueOf(args[0]);
        }
        System.out.println("[AgentOffre] Agent démarré : " + getLocalName());
        System.out.println("[AgentOffre] ML API URL : " + mlApiUrl);

        addBehaviour(new CyclicBehaviour() {
            @Override
            public void action() {
                ACLMessage msg = receive(MessageTemplate.MatchPerformative(ACLMessage.REQUEST));
                if (msg != null) {
                    try {
                        JsonNode req = mapper.readTree(msg.getContent());

                        ObjectNode payload = mapper.createObjectNode();
                        double prixBase = req.has("prixBase") ? req.get("prixBase").asDouble() : (req.has("prixProduit") ? req.get("prixProduit").asDouble() : 0.0);
                        payload.put("prixBase", prixBase);
                        
                        double prixMin = req.has("prixMin") ? req.get("prixMin").asDouble() : 0.0;
                        payload.put("prixMin", prixMin);
                        
                        double noteVendeur = req.has("noteVendeur") ? req.get("noteVendeur").asDouble() : 4.0;
                        payload.put("noteVendeur", noteVendeur);
                        
                        String categorie = resolveCategorie(req);
                        payload.put("categorie", categorie);

                        ArrayNode similarPrices = mapper.createArrayNode();
                        if (req.has("similarPrices") && req.get("similarPrices").isArray()) {
                            similarPrices = (ArrayNode) req.get("similarPrices");
                        }
                        payload.set("similarPrices", similarPrices);

                        JsonNode response = postJson("/predict/price", payload);

                        // If response needs produitId from old version
                        if(req.has("produitId") && response instanceof ObjectNode) {
                            ((ObjectNode)response).put("produitId", req.get("produitId").asText());
                        }

                        ACLMessage reply = msg.createReply();
                        reply.setPerformative(ACLMessage.INFORM);
                        reply.setContent(mapper.writeValueAsString(response));
                        send(reply);

                        System.out.println("[AgentOffre] Réponse ML /predict/price : " + response);

                    } catch (Exception e) {
                        ACLMessage reply = msg.createReply();
                        reply.setPerformative(ACLMessage.FAILURE);
                        reply.setContent("{\"error\": \"" + e.getMessage().replace("\"", "'") + "\"}");
                        send(reply);
                        System.err.println("[AgentOffre] Erreur : " + e.getMessage());
                    }
                } else {
                    block();
                }
            }
        });
    }

    private String resolveCategorie(JsonNode req) {
        if (req.hasNonNull("categorie") && !req.get("categorie").asText().isBlank()) {
            return req.get("categorie").asText();
        }
        if (req.hasNonNull("nom") || req.hasNonNull("description")) {
            ObjectNode classifyPayload = mapper.createObjectNode();
            classifyPayload.put("nom", req.path("nom").asText(""));
            classifyPayload.put("description", req.path("description").asText(""));
            try {
                JsonNode classifyResponse = postJson("/classify/category", classifyPayload);
                if (classifyResponse.hasNonNull("categorie")) {
                    return classifyResponse.get("categorie").asText("autre");
                }
            } catch (Exception e) {
                System.err.println("[AgentOffre] Classification catégorie indisponible: " + e.getMessage());
            }
        }
        return "autre";
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
        System.out.println("[AgentOffre] Agent arrêté : " + getLocalName());
    }
}
