package bridge;

import jade.core.AID;
import jade.core.Profile;
import jade.core.ProfileImpl;
import jade.core.Runtime;
import jade.lang.acl.ACLMessage;
import jade.lang.acl.MessageTemplate;
import jade.wrapper.AgentContainer;
import jade.wrapper.AgentController;
import jade.wrapper.gateway.JadeGateway;
import jakarta.annotation.PostConstruct;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * AgentRestBridge: Exposes the JADE agent system as a REST API.
 * Handles platform initialization, agent deployment, and synchronous ACL communication.
 */
@RestController
@RequestMapping("/agent")
public class AgentRestBridge {

    private final ObjectMapper mapper = new ObjectMapper();
    private AgentContainer mainContainer;
    
    // FIX 4: In-memory state to track prixActuel across rounds
    private final Map<String, Double> prixActuelMap = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        try {
            // 1. Start JADE Main Container
            Runtime rt = Runtime.instance();
            Profile p = new ProfileImpl();
            p.setParameter(Profile.MAIN_HOST, "localhost");
            p.setParameter(Profile.GUI, "false");
            mainContainer = rt.createMainContainer(p);

            String mlApiUrl = System.getenv("ML_API_URL");
            if (mlApiUrl == null || mlApiUrl.isEmpty()) {
                mlApiUrl = "http://localhost:5000";
            }

            // 2. Deploy the 3 Agents with their logic
            AgentController offerAgent = mainContainer.createNewAgent("AgentOffre", "agents.AgentOffre", new Object[]{mlApiUrl});
            offerAgent.start();

            AgentController negoAgent = mainContainer.createNewAgent("AgentNegociation", "agents.AgentNegociation", null);
            negoAgent.start();

            AgentController securityAgent = mainContainer.createNewAgent("AgentSecurite", "agents.AgentSecurite", new Object[]{mlApiUrl});
            securityAgent.start();

            // 3. Init JadeGateway with JADE-specific properties
            jade.util.leap.Properties props = new jade.util.leap.Properties();
            props.setProperty(Profile.MAIN_HOST, "localhost");
            JadeGateway.init(null, props);

            System.out.println(">>> JADE Platform [v4.6.0] initialized successfully with 3 agents.");
        } catch (Exception e) {
            System.err.println("!!! Critical: JADE Initialization Failed: " + e.getMessage());
            e.printStackTrace();
        }
    }

    @PostMapping("/offre/generer")
    public ResponseEntity<?> genererOffre(@RequestBody Map<String, Object> request) {
        return contactAgent("AgentOffre", ACLMessage.REQUEST, request);
    }

    @PostMapping("/nego/ajuster")
    public ResponseEntity<?> ajusterNego(@RequestBody Map<String, Object> request) {
        String negoId = (String) request.get("negociationId");
        
        // FIX 4: Override prixActuel if we have a tracked price for this negotiation
        if (negoId != null && prixActuelMap.containsKey(negoId)) {
            double lastPrice = prixActuelMap.get(negoId);
            System.out.println("[Bridge] Overriding prixActuel for " + negoId + ": " + lastPrice);
            request.put("prixActuel", lastPrice);
        }

        ResponseEntity<?> response = contactAgent("AgentNegociation", ACLMessage.PROPOSE, request);
        
        if (response.getStatusCode() == HttpStatus.OK) {
            @SuppressWarnings("unchecked")
            Map<String, Object> body = (Map<String, Object>) response.getBody();
            if (body != null && body.containsKey("nouveauPrix")) {
                double nouveauPrix = ((Number) body.get("nouveauPrix")).doubleValue();
                boolean isFinal = (Boolean) body.getOrDefault("isFinalOffer", false);
                
                if (isFinal) {
                    System.out.println("[Bridge] Negotiation " + negoId + " finalized. Removing from state.");
                    prixActuelMap.remove(negoId);
                } else {
                    System.out.println("[Bridge] Updating state for " + negoId + " -> " + nouveauPrix);
                    prixActuelMap.put(negoId, nouveauPrix);
                }
            }
        }
        return response;
    }

    @PostMapping("/securite/verifier")
    public ResponseEntity<?> verifierSecurite(@RequestBody Map<String, Object> request) {
        return contactAgent("AgentSecurite", ACLMessage.REQUEST, request);
    }

    /**
     * Synchronous communication helper that sends a message to a JADE agent
     * and waits for a response with a 5000ms timeout.
     */
    private ResponseEntity<?> contactAgent(String agentName, int performative, Object payload) {
        try {
            String jsonContent = mapper.writeValueAsString(payload);
            final String[] agentReply = {null};

            JadeGateway.execute(new jade.core.behaviours.OneShotBehaviour() {
                @Override
                public void action() {
                    ACLMessage msg = new ACLMessage(performative);
                    msg.addReceiver(new AID(agentName, AID.ISLOCALNAME));
                    msg.setContent(jsonContent);
                    
                    String replyId = "req_" + System.currentTimeMillis();
                    msg.setReplyWith(replyId);
                    
                    myAgent.send(msg);

                    MessageTemplate mt = MessageTemplate.MatchInReplyTo(replyId);
                    ACLMessage response = myAgent.blockingReceive(mt, 5000);
                    
                    if (response != null) {
                        agentReply[0] = response.getContent();
                    }
                }
            });

            if (agentReply[0] == null) {
                return ResponseEntity.status(HttpStatus.REQUEST_TIMEOUT)
                        .body(Map.of("error", "Agent " + agentName + " timed out"));
            }

            return ResponseEntity.ok(mapper.readValue(agentReply[0], Map.class));

        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Bridge Communication Error: " + e.getMessage()));
        }
    }
}
