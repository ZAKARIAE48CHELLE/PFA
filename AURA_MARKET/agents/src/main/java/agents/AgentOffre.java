package agents;

import jade.core.Agent;
import jade.core.behaviours.CyclicBehaviour;
import jade.lang.acl.ACLMessage;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.ArrayList;
import java.util.List;

/**
 * AgentOffre: Generates intelligent initial offers based on logarithmic discount formulas
 * and market average analysis.
 */
public class AgentOffre extends Agent {
    private final ObjectMapper mapper = new ObjectMapper();

    @Override
    protected void setup() {
        System.out.println("AgentOffre [" + getAID().getLocalName() + "] is ready.");

        addBehaviour(new CyclicBehaviour(this) {
            @Override
            public void action() {
                ACLMessage msg = receive();
                if (msg != null && msg.getPerformative() == ACLMessage.REQUEST) {
                    try {
                        JsonNode root = mapper.readTree(msg.getContent());
                        
                        String produitId = root.has("produitId") ? root.get("produitId").asText() : "unknown";
                        double p = root.has("prixBase") ? root.get("prixBase").asDouble() : 0.0;
                        double prixMin = root.has("prixMin") ? root.get("prixMin").asDouble() : 0.0;
                        String catStr = root.has("categorie") ? root.get("categorie").asText().toLowerCase() : "";
                        float r = root.has("noteVendeur") && root.get("noteVendeur").asDouble() > 0 
                                  ? (float) root.get("noteVendeur").asDouble() : 3.5f;

                        // 1. Determine Category Factor (Cf)
                        double cf = 1.0; // Standard default
                        if (catStr.contains("phone") || catStr.contains("tablet") || 
                            catStr.contains("laptop") || catStr.contains("tv") || catStr.contains("electromenager")) {
                            cf = 0.8; // High value / low margin
                        } else if (catStr.contains("accessoire") || catStr.contains("audio") || 
                                   catStr.contains("cable") || catStr.contains("coque") || 
                                   catStr.contains("souris") || catStr.contains("casque")) {
                            cf = 1.3; // High margin / accessories
                        }

                        // 2. Compute Base Discount (D)
                        double logP = Math.log10(p + 1);
                        double d = Math.min(50, Math.max(5, (10 + 4 * logP + 3 * (4.5 - r)) * cf));
                        
                        double prixSuggere = p * (1 - d / 100);
                        prixSuggere = Math.max(prixMin, prixSuggere);

                        // 3. Market Analysis Factor
                        double marketFactor = 1.0;
                        if (root.has("similarPrices") && root.get("similarPrices").isArray() && root.get("similarPrices").size() > 0) {
                            List<Double> similar = new ArrayList<>();
                            for (JsonNode priceNode : root.get("similarPrices")) {
                                similar.add(priceNode.asDouble());
                            }
                            double avgSimilar = similar.stream().mapToDouble(Double::doubleValue).average().orElse(p);
                            marketFactor = avgSimilar / p;

                            if (marketFactor < 0.9) {
                                prixSuggere *= 0.95; // Market cheaper, lower more
                            } else if (marketFactor > 1.1) {
                                prixSuggere *= 1.03; // Market expensive, raise slightly
                            }
                            // Re-clamp after market adjustment
                            prixSuggere = Math.max(prixMin, prixSuggere);
                        }

                        // 4. Build Response JSON
                        ObjectNode response = mapper.createObjectNode();
                        response.put("produitId", produitId);
                        response.put("prixSuggere", Math.round(prixSuggere * 100.0) / 100.0);
                        response.put("discountPercent", Math.round(d * 10.0) / 10.0);
                        response.put("marketFactor", Math.round(marketFactor * 100.0) / 100.0);
                        response.put("cf", cf);

                        ACLMessage reply = msg.createReply();
                        reply.setPerformative(ACLMessage.INFORM);
                        reply.setContent(mapper.writeValueAsString(response));
                        send(reply);

                    } catch (Exception e) {
                        e.printStackTrace();
                        ACLMessage reply = msg.createReply();
                        reply.setPerformative(ACLMessage.FAILURE);
                        reply.setContent("{\"error\":\"" + e.getMessage() + "\"}");
                        send(reply);
                    }
                } else {
                    block();
                }
            }
        });
    }
}
