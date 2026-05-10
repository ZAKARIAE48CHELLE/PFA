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
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.web.bind.annotation.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.auramarket.agents.service.KimiService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.client.RestTemplate;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

import java.util.Map;
import java.util.HashMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.ArrayList;
import java.util.List;

/**
 * AgentRestBridge: Exposes the JADE agent system as a REST API.
 * Handles platform initialization, agent deployment, and synchronous ACL communication.
 */
@RestController
@RequestMapping("/agent")
@EnableScheduling
public class AgentRestBridge {

    private final ObjectMapper mapper = new ObjectMapper();
    private AgentContainer mainContainer;
    
    public static class NegotiationState {
        public double prixActuel;
        public double prixPlancher;
        public int roundActuel;
        public List<Double> historiqueOffres;
        public String lastBuyerBehavior;
        public String lastBuyerTrend;
        public long lastUpdated;

        public NegotiationState(double prixActuel, double prixPlancher, int roundActuel) {
            this.prixActuel = prixActuel;
            this.prixPlancher = prixPlancher;
            this.roundActuel = roundActuel;
            this.historiqueOffres = new ArrayList<>();
            this.lastBuyerBehavior = "INITIAL";
            this.lastBuyerTrend = "STABLE";
            this.lastUpdated = System.currentTimeMillis();
        }
    }

    private final Map<String, NegotiationState> stateMap = new ConcurrentHashMap<>();

    @Scheduled(fixedRate = 1800000)
    public void cleanupStateMap() {
        long now = System.currentTimeMillis();
        stateMap.entrySet().removeIf(e -> (now - e.getValue().lastUpdated) > 1800000);
        System.out.println("[BRIDGE] Cleanup NegotiationState completed. Active sessions: " + stateMap.size());
    }

    @Autowired
    private KimiService kimiService;

    // AgentAcheteur Session State (Negotiation)
    private final Map<String, Map<String, Object>> sessionState = new ConcurrentHashMap<>();

    // Chatbot context history (Navigation)
    private final Map<String, List<Map<String, String>>> chatHistory = new ConcurrentHashMap<>();
    
    private final RestTemplate externalRestTemplate = new RestTemplate();
    private final String PRODUCT_SERVICE_URL = "http://product-service:8082";

    @PostConstruct
    public void init() {
        try {
            // 1. Start JADE Main Container
            Runtime rt = Runtime.instance();
            Profile p = new ProfileImpl();
            p.setParameter(Profile.MAIN_HOST, "localhost");
            p.setParameter(Profile.GUI, "false");
            mainContainer = rt.createMainContainer(p);

            // ML API URL from environment
            String mlApiUrl = System.getenv("ML_API_URL");
            if (mlApiUrl == null || mlApiUrl.isEmpty()) {
                mlApiUrl = "http://localhost:5000";
            }

            // 2. Deploy the 3 Agents with their logic
            AgentController offerAgent = mainContainer.createNewAgent("AgentOffre", "agents.AgentOffre", new Object[]{mlApiUrl});
            offerAgent.start();

            AgentController negoAgent = mainContainer.createNewAgent("AgentNegociation", "agents.AgentNegociation", new Object[]{kimiService});
            negoAgent.start();

            AgentController securityAgent = mainContainer.createNewAgent("AgentSecurite", "agents.AgentSecurite", new Object[]{mlApiUrl});
            securityAgent.start();

            AgentController buyerAgent = mainContainer.createNewAgent("AgentAcheteur", "agents.AgentAcheteur", new Object[]{kimiService});
            buyerAgent.start();

            // 3. Init JadeGateway with JADE-specific properties
            jade.util.leap.Properties props = new jade.util.leap.Properties();
            props.setProperty(Profile.MAIN_HOST, "localhost");
            JadeGateway.init(null, props);

            System.out.println(">>> JADE Platform [v4.6.0] initialized successfully with 4 agents (including AgentAcheteur).");
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
        
        // --- VALIDATION & LOGGING prixPlancher ---
        Object pMin = request.get("prixMin");
        double prixPlancher = (pMin instanceof Number) ? ((Number) pMin).doubleValue() : 0.0;
        double pActuel = (request.get("prixActuel") instanceof Number) ? ((Number) request.get("prixActuel")).doubleValue() : 0.0;
        
        System.out.println("[Bridge] Nego " + negoId + " | prixPlancher source: " + prixPlancher);
        
        if (prixPlancher <= 0 || (pActuel > 0 && prixPlancher >= pActuel)) {
            System.err.println("[Bridge ERROR] prixPlancher invalide (" + prixPlancher + ") pour prixActuel (" + pActuel + ")");
            return ResponseEntity.badRequest().body(Map.of(
                "error", "Prix cible invalide",
                "prixActuel", pActuel
            ));
        }
        System.out.println("[BRIDGE VALIDATION] prixPlancher=" + prixPlancher + " prixActuel=" + pActuel);
        
        // FIX: Maintain complete state per negotiation
        double prixPropose = (request.get("prixPropose") instanceof Number) ? ((Number) request.get("prixPropose")).doubleValue() : 0.0;
        
        NegotiationState state = stateMap.computeIfAbsent(negoId, k -> new NegotiationState(pActuel, prixPlancher, 1));
        
        // [LOGGING] Debug state issues
        System.out.println("[STATE] negoId=" + negoId 
            + " prixActuel=" + state.prixActuel
            + " prixPlancher=" + state.prixPlancher  
            + " round=" + state.roundActuel
            + " historique=" + state.historiqueOffres);

        if (prixPropose > 0) {
            state.historiqueOffres.add(prixPropose);
        }
        state.lastUpdated = System.currentTimeMillis();
        
        // Ensure request uses the state
        request.put("prixActuel", state.prixActuel);
        request.put("historiqueOffres", state.historiqueOffres);
        request.put("roundActuel", state.roundActuel);
        
        ResponseEntity<?> response = contactAgent("AgentNegociation", ACLMessage.PROPOSE, request);
        
        if (response.getStatusCode() == HttpStatus.OK) {
            @SuppressWarnings("unchecked")
            Map<String, Object> body = (Map<String, Object>) response.getBody();
            if (body != null && body.containsKey("nouveauPrix")) {
                double nouveauPrix = ((Number) body.get("nouveauPrix")).doubleValue();
                boolean isFinal = (Boolean) body.getOrDefault("isFinalOffer", false);
                
                // FIX: Le vendeur ne peut JAMAIS remonter son prix
                if (nouveauPrix < state.prixActuel) {
                    state.prixActuel = nouveauPrix;
                } else {
                    System.out.println("[GUARD] Tentative de hausse de prix bloquée : " + nouveauPrix + " MAD > " + state.prixActuel + " MAD");
                }
                state.roundActuel++;
                state.lastUpdated = System.currentTimeMillis();
                
                System.out.println("[BRIDGE] negociationId=" + negoId + " round=" + state.roundActuel + " prixActuel=" + state.prixActuel + " historiqueOffres=" + state.historiqueOffres);
                
                if (isFinal) {
                    System.out.println("[Bridge] Negotiation " + negoId + " finalized. Removing from state.");
                    stateMap.remove(negoId);
                }
            }
        }
        return response;
    }

    @PostMapping("/securite/verifier")
    public ResponseEntity<?> verifierSecurite(@RequestBody Map<String, Object> request) {
        return contactAgent("AgentSecurite", ACLMessage.REQUEST, request);
    }

    // --- New Commentary & Navigation Endpoints ---

    @PostMapping("/acheteur/commenter")
    public ResponseEntity<?> commenterNegociation(@RequestBody Map<String, Object> request) {
        String systemPrompt = "Tu es Aura, l'assistante AuraMarket. " +
            "Tu commentes la négociation pour l'acheteur de façon naturelle. " +
            "RÈGLES ABSOLUES : " +
            "- Ne jamais mentionner les chiffres exacts de réduction " +
            "  (pas de 'réduction de X MAD') " +
            "- Ne jamais mentionner le prix précédent " +
            "- Ne jamais mentionner prixMin ou prix plancher " +
            "- 1 seule phrase, ton conversationnel et encourageant " +
            "- Parler du vendeur à la 3ème personne " +
            "EXEMPLES DE BONNES RÉPONSES : " +
            "'Le vendeur fait un geste, c'est encourageant !' " +
            "'Bonne nouvelle, le vendeur montre de la flexibilité.' " +
            "'Le vendeur résiste encore, mais continuez !' " +
            "'La négociation avance dans le bon sens.'";

        String userMsg = String.format(
            "Comportement vendeur: %s. Tendance: %s. " +
            "L'acheteur doit-il être encouragé ou prudent ?",
            request.get("buyerBehavior"),
            request.get("buyerTrend")
        );
        
        String response = kimiService.askKimi(systemPrompt, userMsg, "COMMENT");
        return ResponseEntity.ok(Map.of("message", response));
    }

    @PostMapping("/chat/navigate")
    public ResponseEntity<?> chatNavigate(@RequestBody Map<String, Object> request) {
        String sessionId = (String) request.get("sessionId");
        String userMessage = (String) request.get("message");
        
        // Retrieve and format history for this session
        List<Map<String, String>> history = chatHistory.getOrDefault(sessionId, new ArrayList<>());
        
        // 1. Intent Detection
        String intentPrompt = """
Tu es Aura, l'assistant IA d'AuraMarket marketplace marocaine.
Tu dois TOUJOURS répondre en JSON valide, rien d'autre.
Langue de réponse : même langue que l'utilisateur 
(français si français, anglais si anglais, darija si darija).

FORMAT OBLIGATOIRE :
{
  "intention": "SEARCH_PRODUCT" | "VIEW_CATEGORY" | "CHECK_ORDER" | "GENERAL",
  "categorie": "Téléphones" | "Informatique" | "Électroménager" | null,
  "recherche": "mot clé produit ou null",
  "prixMax": null ou nombre,
  "reponse": "Ton message naturel pour l'utilisateur"
}

RÈGLES DE CLASSIFICATION :
- Mention d'un produit (iPhone, laptop, télé...) → SEARCH_PRODUCT
- Question sur commande/livraison/statut → CHECK_ORDER  
- Salutation/question générale → GENERAL
- reponse doit toujours être utile et naturelle, jamais vide

EXEMPLES :
User: "i want to buy an iphone 15"
→ {"intention":"SEARCH_PRODUCT","categorie":"Téléphones",
   "recherche":"iPhone 15","prixMax":null,
   "reponse":"Let me find iPhone 15 options for you!"}

User: "hey"
→ {"intention":"GENERAL","categorie":null,
   "recherche":null,"prixMax":null,
   "reponse":"Bonjour ! Comment puis-je vous aider aujourd'hui ?"}

User: "where is my order"
→ {"intention":"CHECK_ORDER","categorie":null,
   "recherche":null,"prixMax":null,
   "reponse":"Let me check the status of your orders."}
""";
        
        String llmIntent = kimiService.askKimi(intentPrompt, userMessage, history, "NAV");
        Map<String, Object> intent;
        try {
            int start = llmIntent.indexOf("{");
            int end = llmIntent.lastIndexOf("}");
            if (start != -1 && end != -1 && start < end) {
                intent = mapper.readValue(llmIntent.substring(start, end + 1), Map.class);
            } else {
                throw new Exception("No JSON block found in response");
            }
        } catch (Exception e) {
            System.err.println("[CHAT_NAVIGATE] Intent parse error: " + e.getMessage());
            System.err.println("[CHAT_NAVIGATE] LLM raw response: " + llmIntent);
            
            if (llmIntent != null && llmIntent.trim().length() > 10 
                && !llmIntent.contains("Exception")) {
                String cleaned = llmIntent
                    .replaceAll("(?si)<think>.*?(</think>|$)", "")
                    .trim();
                
                // Si la réponse ressemble à un JSON coupé, on force le fallback par mot-clé
                if (!cleaned.startsWith("{")) {
                    return ResponseEntity.ok(Map.of(
                        "type", "GENERAL", 
                        "reponse", cleaned
                    ));
                }
            }
            
            String lower = userMessage.toLowerCase();
            String fallbackReponse;
            String fallbackType;
            
            if (lower.contains("iphone") || lower.contains("laptop") || 
                lower.contains("téléphone") || lower.contains("phone") ||
                lower.contains("produit") || lower.contains("cherche") ||
                lower.contains("disponible") || lower.contains("available")) {
                fallbackReponse = "Je recherche ça pour vous...";
                fallbackType = "SEARCH_PRODUCT";
            } else if (lower.contains("commande") || lower.contains("order") ||
                       lower.contains("livraison") || lower.contains("statut")) {
                fallbackReponse = "Je vérifie vos commandes...";
                fallbackType = "CHECK_ORDER";
            } else {
                fallbackReponse = "Bonjour ! Je peux vous aider à trouver " +
                                  "des produits ou suivre vos commandes.";
                fallbackType = "GENERAL";
            }
            
            return ResponseEntity.ok(Map.of(
                "type", fallbackType, 
                "reponse", fallbackReponse
            ));
        }

        String intention = (String) intent.get("intention");
        String agentResponse = (String) intent.get("reponse");

        // Update History (Limit to 5 last messages)
        history.add(Map.of("role", "user", "content", userMessage));
        history.add(Map.of("role", "assistant", "content", agentResponse));
        if (history.size() > 10) { // 5 exchanges = 10 messages
            history = history.subList(history.size() - 10, history.size());
        }
        chatHistory.put(sessionId, history);

        Map<String, Object> result = new HashMap<>();
        result.put("type", intention);
        result.put("reponse", agentResponse);

        // 2. Data Retrieval based on Intent
        if ("SEARCH_PRODUCT".equals(intention) || "VIEW_CATEGORY".equals(intention)) {
            try {
                // Forward JWT Token
                HttpHeaders headers = new HttpHeaders();
                ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
                if (attrs != null) {
                    String authHeader = attrs.getRequest().getHeader("Authorization");
                    if (authHeader != null) headers.set("Authorization", authHeader);
                }
                
                HttpEntity<String> entity = new HttpEntity<>(headers);
                
                // Build URL with optional category and search filters
                String category = (String) intent.get("categorie");
                String recherche = (String) intent.get("recherche");
                
                StringBuilder urlBuilder = new StringBuilder(PRODUCT_SERVICE_URL + "/products?");
                if (category != null && !category.isEmpty()) {
                    urlBuilder.append("category=").append(category).append("&");
                }
                if (recherche != null && !recherche.isEmpty()) {
                    urlBuilder.append("search=")
                              .append(java.net.URLEncoder.encode(recherche, "UTF-8"))
                              .append("&");
                }
                
                String url = urlBuilder.toString();
                if (url.endsWith("&") || url.endsWith("?")) {
                    url = url.substring(0, url.length() - 1);
                }
                
                ResponseEntity<List> productsRes = externalRestTemplate.exchange(url, org.springframework.http.HttpMethod.GET, entity, List.class);
                
                if (productsRes.getStatusCode().is2xxSuccessful()) {
                    List<Map<String, Object>> all = productsRes.getBody();
                    // Map to a cleaner format and ensure IDs are strings
                    List<Map<String, Object>> clean = all.stream().limit(3).map(p -> {
                        Map<String, Object> m = new HashMap<>();
                        m.put("id", p.get("id").toString());
                        m.put("titre", p.get("titre"));
                        m.put("prix", p.get("prix"));
                        m.put("imageUrl", p.get("imageUrl"));
                        m.put("categorie", p.get("categorie"));
                        return m;
                    }).toList();
                    result.put("produits", clean);
                }
            } catch (Exception e) {
                System.err.println("[CHAT_NAVIGATE] Product fetch error for intent: " + intention + " | Error: " + e.getMessage());
            }
        } else if ("CHECK_ORDER".equals(intention)) {
            try {
                // Forward JWT Token
                HttpHeaders headers = new HttpHeaders();
                ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
                if (attrs != null) {
                    String authHeader = attrs.getRequest().getHeader("Authorization");
                    if (authHeader != null) headers.set("Authorization", authHeader);
                }
                
                HttpEntity<String> entity = new HttpEntity<>(headers);
                
                // Get userId from request payload
                Object userIdObj = request.get("userId");
                if (userIdObj != null && !userIdObj.toString().isEmpty() && !"null".equals(userIdObj.toString())) {
                    String userId = userIdObj.toString();
                    String url = PRODUCT_SERVICE_URL + "/commandes/acheteur/" + userId;
                    ResponseEntity<List> ordersRes = externalRestTemplate.exchange(url, org.springframework.http.HttpMethod.GET, entity, List.class);
                    
                    if (ordersRes.getStatusCode().is2xxSuccessful()) {
                        List<Map<String, Object>> orders = ordersRes.getBody();
                        result.put("commandes", orders != null ? orders.stream().limit(3).toList() : new ArrayList<>());
                    }
                }
            } catch (Exception e) {
                System.err.println("[CHAT_NAVIGATE] Order fetch error: " + e.getMessage());
            }
        }
        
        return ResponseEntity.ok(result);
    }

    private String getNavigationFallback(String intention) {
        return switch (intention) {
            case "SEARCH_PRODUCT" -> "Consultez notre catalogue complet sur /list-produit";
            case "CHECK_ORDER"    -> "Retrouvez vos commandes sur /commandes";
            case "NEGOTIATE"      -> "Ouvrez la fiche produit pour lancer une négociation";
            default               -> "Comment puis-je vous aider sur AuraMarket ?";
        };
    }

    // --- AgentAcheteur Endpoints ---

    @PostMapping("/acheteur/chat")
    public ResponseEntity<?> acheteurChat(@RequestBody Map<String, Object> request) {
        request.put("mode", "CHAT");
        return contactAgent("AgentAcheteur", ACLMessage.REQUEST, request);
    }

    @PostMapping("/acheteur/nego/start")
    public ResponseEntity<?> acheteurNegoStart(@RequestBody Map<String, Object> request) {
        
        // Validation budget vs prixPlancher
        double prixCible = ((Number) request.get("prixCible")).doubleValue();
        double prixPlancher = ((Number) request.get("prixMin")).doubleValue();
        double prixActuel = ((Number) request.get("prixActuel")).doubleValue();
        
        System.out.println("[BRIDGE] AUTO start — prixCible=" + prixCible 
                         + " prixPlancher=" + prixPlancher + " prixActuel=" + prixActuel);
        
        // Cas 1 : Budget sous le plancher → impossible
        if (prixCible < prixPlancher) {
            String msg = kimiService.askKimi(
                "Tu es Aura, assistant AuraMarket. " +
                "RÈGLE ABSOLUE : ne jamais mentionner le prix minimum " +
                "du vendeur — c'est confidentiel. " +
                "Réponds en 1-2 phrases bienveillantes.",
                String.format("Le budget du client (%.2f MAD) est trop bas " +
                    "pour ce produit. Explique sans mentionner de chiffre " +
                    "minimum que l'accord automatique est impossible et " +
                    "suggère de négocier manuellement.", prixCible),
                "AUTO"
            );
            return ResponseEntity.ok(Map.of(
                "accordTrouve",  false,
                "isFinalOffer",  true,
                "impossible",    true,
                "prixCible",     prixCible,
                "reponse",       msg != null ? msg : 
                    "Votre budget de " + String.format("%.2f", prixCible) + " MAD est trop bas pour ce produit. " +
                    "Essayez de négocier manuellement ou augmentez votre budget."
            ));
        }
        
        // Cas 2 : Budget = prixActuel → accepter directement
        if (prixCible >= prixActuel) {
            return ResponseEntity.ok(Map.of(
                "accordTrouve", true,
                "isFinalOffer", true,
                "nouveauPrix",  prixActuel,
                "reponse",      "Votre budget couvre le prix demandé. " +
                               "Vous pouvez accepter l'offre directement !"
            ));
        }
        
        // Cas normal → lancer la négociation
        String sessionId = (String) request.get("sessionId");
        String negoId = (String) request.get("negociationId");
        
        // Toujours réinitialiser le state pour une nouvelle AUTO
        NegotiationState freshState = new NegotiationState(
            prixActuel,   // prix actuel du moment
            prixPlancher, 
            1             // toujours repartir du round 1
        );
        stateMap.put(negoId + "_auto_" + sessionId, freshState);
        
        // Utiliser ce negoId séparé pour ne pas polluer 
        // la négo manuelle existante
        request.put("negociationId", negoId + "_auto_" + sessionId);
        
        request.put("mode", "NEGO_AUTO");
        sessionState.put(sessionId, new HashMap<>(request));
        return contactAgent("AgentAcheteur", ACLMessage.REQUEST, request);
    }

    @PostMapping("/acheteur/nego/message")
    public ResponseEntity<?> acheteurNegoMessage(@RequestBody Map<String, Object> request) {
        String sessionId = (String) request.get("sessionId");
        Map<String, Object> session = sessionState.getOrDefault(sessionId, new HashMap<>());
        
        // Merge session data into request
        request.put("mode", "NEGO_MANUEL");
        request.putIfAbsent("prixCible", session.get("prixCible"));
        request.putIfAbsent("prixActuel", session.get("prixActuel"));
        request.putIfAbsent("historiqueOffres", session.getOrDefault("historiqueOffres", new ArrayList<>()));
        request.putIfAbsent("roundActuel", session.getOrDefault("roundActuel", 1));
        
        ResponseEntity<?> response = contactAgent("AgentAcheteur", ACLMessage.REQUEST, request);
        
        if (response.getStatusCode() == HttpStatus.OK) {
            // Update session with new round/history if needed
            Map<String, Object> body = (Map<String, Object>) response.getBody();
            if (body != null && body.containsKey("prixPropose")) {
                List<Double> history = (List<Double>) session.getOrDefault("historiqueOffres", new ArrayList<>());
                history.add(((Number) body.get("prixPropose")).doubleValue());
                session.put("historiqueOffres", history);
                session.put("roundActuel", ((Number) session.getOrDefault("roundActuel", 1)).intValue() + 1);
                sessionState.put(sessionId, session);
            }
        }
        
        return response;
    }

    /**
     * Synchronous communication helper that sends a message to a JADE agent
     * and waits for a response with a 300s timeout (5 min for multi-round AI negotiations).
     */
    private ResponseEntity<?> contactAgent(String agentName, int performative, Object payload) {
        try {
            // Forward JWT Token if present
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                HttpServletRequest currentRequest = attrs.getRequest();
                String authHeader = currentRequest.getHeader("Authorization");
                if (authHeader != null && payload instanceof Map) {
                    ((Map<String, Object>) payload).put("jwtToken", authHeader);
                }
            }

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
                    ACLMessage response = myAgent.blockingReceive(mt, 300000); // 5 min for multi-round AI
                    
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
