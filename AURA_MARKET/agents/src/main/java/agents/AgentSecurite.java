package agents;

import jade.core.Agent;
import jade.core.behaviours.CyclicBehaviour;
import jade.lang.acl.ACLMessage;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

/**
 * AgentSecurite: Detects pricing anomalies and red flags, proposing safe alternatives
 * when an offer is deemed suspect.
 */
public class AgentSecurite extends Agent {
    private final ObjectMapper mapper = new ObjectMapper();

    @Override
    protected void setup() {
        System.out.println("AgentSecurite [" + getAID().getLocalName() + "] is ready.");

        addBehaviour(new CyclicBehaviour(this) {
            @Override
            public void action() {
                ACLMessage msg = receive();
                if (msg != null && msg.getPerformative() == ACLMessage.REQUEST) {
                    try {
                        JsonNode root = mapper.readTree(msg.getContent());
                        
                        String offreId = root.get("offreId").asText();
                        double prixOffre = root.get("prixOffre").asDouble();
                        double prixProduit = root.get("prixProduit").asDouble();
                        double seuil = root.has("seuilAnomalie") ? root.get("seuilAnomalie").asDouble() : 0.30;

                        // 1. Anomaly Logic
                        double ratio = (prixProduit > 0) ? Math.abs(prixProduit - prixOffre) / prixProduit : 0;
                        boolean isSuspect = false;
                        String reason = "None";

                        if (ratio > seuil) {
                            isSuspect = true;
                            reason = "Price deviation of " + Math.round(ratio * 100) + "% exceeds threshold";
                        } else if (prixOffre <= 0) {
                            isSuspect = true;
                            reason = "Price is zero or negative";
                        } else if (prixOffre > prixProduit * 2.0) {
                            isSuspect = true;
                            reason = "Price is more than double the base price (unlikely luxury markup)";
                        } else if (prixOffre < prixProduit * 0.1) {
                            isSuspect = true;
                            reason = "Price is less than 10% of base price (suspiciously low)";
                        }

                        // 2. Build Response
                        ObjectNode response = mapper.createObjectNode();
                        response.put("offreId", offreId);
                        response.put("isSuspect", isSuspect);
                        response.put("anomalyRatio", Math.round(ratio * 100.0) / 100.0);
                        response.put("reason", reason);

                        ArrayNode alts = response.putArray("alternatives");
                        if (isSuspect && prixProduit > 0) {
                            alts.add(Math.round(prixProduit * 0.85 * 100.0) / 100.0); // 15% discount
                            alts.add(Math.round(prixProduit * 0.75 * 100.0) / 100.0); // 25% discount
                            alts.add(Math.round(prixProduit * 0.60 * 100.0) / 100.0); // 40% discount
                        }

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
