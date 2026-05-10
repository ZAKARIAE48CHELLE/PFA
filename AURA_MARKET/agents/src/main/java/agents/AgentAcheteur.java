package agents;

import jade.core.Agent;
import jade.core.AID;
import jade.core.behaviours.CyclicBehaviour;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.auramarket.agents.service.KimiService;
import com.auramarket.agents.strategy.BuyerNegotiationStrategy;

import java.util.*;

/**
 * AgentAcheteur: IA side for the buyer.
 * Handles Chat (Kimi LLM) and Negotiation (AUTO/MANUAL).
 */
public class AgentAcheteur extends Agent {

    private final ObjectMapper mapper = new ObjectMapper();
    private KimiService kimiService;

    @Override
    protected void setup() {
        Object[] args = getArguments();
        if (args != null && args.length > 0) {
            this.kimiService = (KimiService) args[0];
        }

        System.out.println("[AgentAcheteur] Démarrage : " + getLocalName());

        addBehaviour(new CyclicBehaviour() {
            @Override
            public void action() {
                ACLMessage msg = receive(MessageTemplate.MatchPerformative(ACLMessage.REQUEST));
                if (msg != null) {
                    try {
                        Map<String, Object> input = mapper.readValue(msg.getContent(), Map.class);
                        String mode = (String) input.getOrDefault("mode", "CHAT");
                        Map<String, Object> response;

                        if ("NEGO_AUTO".equals(mode)) {
                            response = handleAutoNego(input);
                        } else if ("NEGO_MANUEL".equals(mode)) {
                            response = handleManualNego(input);
                        } else {
                            response = handleChat(input);
                        }

                        ACLMessage reply = msg.createReply();
                        reply.setPerformative(ACLMessage.INFORM);
                        reply.setContent(mapper.writeValueAsString(response));
                        send(reply);

                    } catch (Exception e) {
                        System.err.println("[AgentAcheteur] Erreur : " + e.getMessage());
                        e.printStackTrace();
                    }
                } else {
                    block();
                }
            }
        });
    }

    private Map<String, Object> handleChat(Map<String, Object> input) {
        String message = (String) input.get("message");
        String sessionId = (String) input.get("sessionId");
        
        String systemPrompt = "Tu es l'assistant IA d'AuraMarket, une marketplace marocaine intelligente. " +
                "Tu aides les acheteurs à naviguer, trouver des produits et comprendre leurs commandes. " +
                "COMPORTEMENT : Réponds en français, de façon concise et amicale (max 2-3 phrases). " +
                "Si question sur un produit spécifique → demande des détails. " +
                "Si utilisateur veut négocier → explique les deux modes : AUTO (l'agent négocie seul) et MANUEL (le client propose).";
        
        String responseText = kimiService.askKimi(systemPrompt, message, "CHAT");
        
        Map<String, Object> res = new HashMap<>();
        res.put("sessionId", sessionId);
        res.put("type", "CHAT");
        res.put("reponse", responseText);
        return res;
    }

    private Map<String, Object> handleManualNego(Map<String, Object> input) {
        double prixCible = toDouble(input.get("prixCible"));
        double prixActuel = toDouble(input.get("prixActuel"));
        String lastAgentResponse = (String) input.get("lastAgentResponse");
        
        String systemPrompt = "Tu es l'assistant IA d'AuraMarket côté ACHETEUR. Le client négocie lui-même mais tu l'aides à décider son prochain prix. " +
                "COMPORTEMENT : Explique ce que le vendeur vient de proposer en 1 phrase naturelle. " +
                "Suggère un prochain prix à proposer avec une justification courte. " +
                "Ne dépasse jamais le budget client (" + prixCible + " MAD). Réponds en français, max 3 phrases.";
        
        String userMsg = String.format("Vendeur propose: %.2f. Client veut: %.2f. Dernier message vendeur: %s", 
                                        prixActuel, prixCible, lastAgentResponse);
        
        String responseText = kimiService.askKimi(systemPrompt, userMsg, "NEGO");
        
        Map<String, Object> res = new HashMap<>();
        res.put("sessionId", input.get("sessionId"));
        res.put("type", "NEGO_SUGGESTION");
        res.put("reponse", responseText);
        return res;
    }

    private Map<String, Object> handleAutoNego(Map<String, Object> input) {
        double prixCible = toDouble(input.get("prixCible"));
        double prixActuel = toDouble(input.get("prixActuel"));
        double prixPlancher = toDouble(input.get("prixMin"));
        int roundActuel = toInt(input.get("roundActuel"));
        int roundsMax = 5; // Cap at 5 for stability with 8B model
        List<Double> history = (List<Double>) input.getOrDefault("historiqueOffres", new ArrayList<>());
        String negociationId = (String) input.get("negociationId");

        String systemPrompt = "Tu es l'agent négociateur IA d'AuraMarket. Tu négocies à la place du client pour obtenir le meilleur prix possible. " +
                "STRATÉGIE : Round 1: propose 72% du prix actuel. Si vendeur DECLINING -> monte de 3% max. Si STABLE -> 5%. Si IMPROVING -> 7%. " +
                "Ne dépasse JAMAIS le budget client (" + prixCible + "). " +
                "FORMAT DE RÉPONSE (JSON strict): {\"prixPropose\": number, \"message\": \"...\", \"raisonnement\": \"...\"}";

        boolean accordTrouve = false;
        double prixAccord = 0;
        String finalMessage = "";
        String sellerTrend = "STABLE";

        while (roundActuel <= roundsMax) {
            if (prixActuel <= prixCible) {
                accordTrouve = true;
                prixAccord = prixActuel;
                finalMessage = "Accord trouvé à " + prixAccord + " MAD !";
                break;
            }

            // LLM call removed here to prevent massive latency.
            // In NEGO_AUTO, the user does not read individual round messages.
            // The numerical offer is calculated below using the mathematical strategy.
            // Strictly calculate the next offer based on strategy
            double nextOffer = com.auramarket.agents.strategy.BuyerNegotiationStrategy.calculateNextOffer(
                prixCible, prixActuel, sellerTrend, roundActuel, history, roundsMax
            );
            
            // Call AgentNegociation
            Map<String, Object> negoRequest = new HashMap<>();
            negoRequest.put("negociationId", negociationId);
            negoRequest.put("prixActuel", prixActuel);
            negoRequest.put("prixMin", prixPlancher);
            negoRequest.put("prixPropose", nextOffer);
            negoRequest.put("roundActuel", roundActuel);
            negoRequest.put("roundsMax", roundsMax);
            negoRequest.put("historiqueOffres", history);

            Map<String, Object> sellerResponse = callAgent("AgentNegociation", negoRequest);
            if (sellerResponse == null) break;

            prixActuel = toDouble(sellerResponse.get("nouveauPrix"));
            sellerTrend = (String) sellerResponse.getOrDefault("buyerTrend", "STABLE");
            boolean isFinalOffer = (Boolean) sellerResponse.getOrDefault("isFinalOffer", false);

            history.add(nextOffer);
            roundActuel++;

            if (prixActuel <= prixCible) {
                accordTrouve = true;
                prixAccord = prixActuel;
                finalMessage = "Accord trouvé à " + prixAccord + " MAD !";
                break;
            }
            if (isFinalOffer && prixActuel > prixCible) {
                finalMessage = "Le vendeur reste ferme sur " + prixActuel + " MAD.";
                break;
            }
        }

        Map<String, Object> res = new HashMap<>();
        res.put("sessionId", input.get("sessionId"));
        res.put("type", "NEGO_RESULT");
        res.put("reponse", finalMessage);
        res.put("prixAccord", prixAccord);
        res.put("prixFinal", prixActuel); // The latest seller offer
        res.put("accordTrouve", accordTrouve);
        res.put("roundActuel", roundActuel);
        return res;
    }

    private Map<String, Object> callAgent(String agentName, Map<String, Object> payload) {
        try {
            ACLMessage msg = new ACLMessage(ACLMessage.PROPOSE);
            msg.addReceiver(new AID(agentName, AID.ISLOCALNAME));
            msg.setContent(mapper.writeValueAsString(payload));
            String replyId = "req_" + System.currentTimeMillis();
            msg.setReplyWith(replyId);
            send(msg);

            MessageTemplate mt = MessageTemplate.MatchInReplyTo(replyId);
            ACLMessage response = blockingReceive(mt, 300000);
            if (response != null) {
                return mapper.readValue(response.getContent(), Map.class);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private double toDouble(Object o) { return o instanceof Number ? ((Number) o).doubleValue() : 0.0; }
    private int toInt(Object o) { return o instanceof Number ? ((Number) o).intValue() : 0; }
}
