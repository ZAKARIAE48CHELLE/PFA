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
import com.auramarket.agents.config.SystemPrompts;
import com.auramarket.agents.strategy.BuyerNegotiationStrategy;
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
import java.util.regex.Pattern;
import java.util.regex.Matcher;

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
    
    public static class ManualNegotiationState {
        public String negociationId;
        public String produitId;
        public String acheteurId;
        public double prixInitial;
        public double prixActuel;
        public double prixMin;
        public int roundActuel;
        public int roundsMax;
        public List<Double> buyerManualOffers;
        public List<Double> sellerResponses;
        public String status;
        public boolean closed;
        public long lastUpdated;

        public ManualNegotiationState(String negociationId, double prixInitial, double prixActuel, double prixMin, int roundsMax) {
            this.negociationId = negociationId;
            this.prixInitial = prixInitial;
            this.prixActuel = prixActuel;
            this.prixMin = prixMin;
            this.roundActuel = 1;
            this.roundsMax = roundsMax;
            this.buyerManualOffers = new ArrayList<>();
            this.sellerResponses = new ArrayList<>();
            this.status = "IN_PROGRESS";
            this.closed = false;
            this.lastUpdated = System.currentTimeMillis();
        }
    }

    public static class AutoRoundTrace {
        public int round;
        public double buyerOffer;
        public double sellerResponse;
        public String buyerBehavior;
        public String buyerTrend;

        public AutoRoundTrace(int round, double buyerOffer, double sellerResponse, String buyerBehavior, String buyerTrend) {
            this.round = round;
            this.buyerOffer = buyerOffer;
            this.sellerResponse = sellerResponse;
            this.buyerBehavior = buyerBehavior;
            this.buyerTrend = buyerTrend;
        }
    }

    public static class AutoNegotiationState {
        public String negociationId;
        public String produitId;
        public String acheteurId;
        public double prixInitial;
        public double prixMin;
        public double budget;
        public int roundsUsed;
        public int roundsMax;
        public List<AutoRoundTrace> trace;
        public String status;
        public boolean autoInProgress;
        public boolean closed;
        public long lastUpdated;

        public AutoNegotiationState(String negociationId, double prixInitial, double prixMin, double budget, int roundsMax) {
            this.negociationId = negociationId;
            this.prixInitial = prixInitial;
            this.prixMin = prixMin;
            this.budget = budget;
            this.roundsUsed = 0;
            this.roundsMax = roundsMax;
            this.trace = new ArrayList<>();
            this.status = "IN_PROGRESS";
            this.autoInProgress = false;
            this.closed = false;
            this.lastUpdated = System.currentTimeMillis();
        }
    }

    private final Map<String, ManualNegotiationState> manualStateMap = new ConcurrentHashMap<>();
    private final Map<String, AutoNegotiationState> autoStateMap = new ConcurrentHashMap<>();

    @Scheduled(fixedRate = 1800000)
    public void cleanupStateMap() {
        long now = System.currentTimeMillis();
        manualStateMap.entrySet().removeIf(e -> (now - e.getValue().lastUpdated) > 1800000);
        autoStateMap.entrySet().removeIf(e -> (now - e.getValue().lastUpdated) > 1800000);
        System.out.println("[BRIDGE] Cleanup completed. Active MANUAL: " + manualStateMap.size() + ", AUTO: " + autoStateMap.size());
    }

    @Autowired
    private KimiService kimiService;

    @Autowired
    private ErrorReporter errorReporter;

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

    @PostMapping("/nego/manual")
    public ResponseEntity<?> manualNego(@RequestBody Map<String, Object> request) {
        String negoId = (String) request.get("negociationId");
        
        double prixPropose = (request.get("prixPropose") instanceof Number) ? ((Number) request.get("prixPropose")).doubleValue() : 0.0;
        double pActuel = (request.get("prixActuel") instanceof Number) ? ((Number) request.get("prixActuel")).doubleValue() : 0.0;
        double prixPlancher = (request.get("prixMin") instanceof Number) ? ((Number) request.get("prixMin")).doubleValue() : 0.0;
        int roundsMax = (request.get("roundsMax") instanceof Number) ? ((Number) request.get("roundsMax")).intValue() : 3;

        System.out.println("[MANUAL_NEGO] negociationId=" + negoId);
        System.out.println("[MANUAL_NEGO] prixActuel=" + pActuel);
        System.out.println("[MANUAL_NEGO] prixPropose=" + prixPropose);
        System.out.println("[MANUAL_NEGO] prixMin=" + prixPlancher);

        if (prixPlancher <= 0 || (pActuel > 0 && prixPlancher >= pActuel)) {
            String errDetail = "[Bridge ERROR] prixPlancher invalide (" + prixPlancher + ") pour prixActuel (" + pActuel + ")";
            System.err.println(errDetail);
            String prodId = request.containsKey("produitId") ? String.valueOf(request.get("produitId")) : null;
            errorReporter.reportConfigError("agents-bridge", errDetail, negoId, prodId);
            return ResponseEntity.badRequest().body(Map.of("status", "INVALID", "message", "Configuration de prix invalide."));
        }

        ManualNegotiationState state = manualStateMap.computeIfAbsent(negoId, k -> 
            new ManualNegotiationState(negoId, pActuel, pActuel, prixPlancher, roundsMax)
        );

        if (state.closed) {
            return ResponseEntity.ok(Map.of(
                "mode", "MANUAL",
                "status", state.status,
                "message", "Cette négociation est déjà terminée.",
                "prixPropose", prixPropose,
                "prixVendeur", state.prixActuel,
                "prixAffiche", state.prixActuel,
                "accordTrouve", "ACCEPTED".equals(state.status),
                "isFinalOffer", true,
                "roundActuel", state.roundActuel,
                "roundsMax", state.roundsMax
            ));
        }

        if (prixPropose < prixPlancher) {
            state.buyerManualOffers.add(prixPropose);
            state.status = "REJECTED";
            System.out.println("[MANUAL_NEGO] status=REJECTED (sous le plancher)");
            return ResponseEntity.ok(Map.of(
                "mode", "MANUAL",
                "status", "REJECTED",
                "message", "Votre offre est trop basse. Le vendeur garde son prix actuel.",
                "prixPropose", prixPropose,
                "prixVendeur", state.prixActuel,
                "prixAffiche", state.prixActuel,
                "accordTrouve", false,
                "isFinalOffer", state.roundActuel >= state.roundsMax,
                "roundActuel", state.roundActuel,
                "roundsMax", state.roundsMax
            ));
        }

        state.buyerManualOffers.add(prixPropose);
        state.lastUpdated = System.currentTimeMillis();

        request.put("prixActuel", state.prixActuel);
        request.put("historiqueOffres", state.buyerManualOffers);
        request.put("roundActuel", state.roundActuel);

        ResponseEntity<?> response = contactAgent("AgentNegociation", ACLMessage.PROPOSE, request);

        if (response.getStatusCode() == HttpStatus.OK) {
            @SuppressWarnings("unchecked")
            Map<String, Object> body = (Map<String, Object>) response.getBody();
            if (body != null && body.containsKey("nouveauPrix")) {
                double nouveauPrix = ((Number) body.get("nouveauPrix")).doubleValue();
                boolean isFinal = (Boolean) body.getOrDefault("isFinalOffer", false);
                String behavior = (String) body.getOrDefault("buyerBehavior", "NORMAL");

                state.sellerResponses.add(nouveauPrix);

                if (nouveauPrix < state.prixActuel) {
                    state.prixActuel = nouveauPrix;
                }

                String status;
                String message;
                double prixAffiche;
                boolean accordTrouve;

                if ("ACCEPTED".equals(behavior) || nouveauPrix <= prixPropose || (isFinal && nouveauPrix == prixPropose)) {
                    status = "ACCEPTED";
                    message = "🎉 Accord trouvé ! Le vendeur accepte votre offre de " + String.format("%.2f", prixPropose) + " MAD.";
                    prixAffiche = prixPropose;
                    accordTrouve = true;
                    state.prixActuel = prixPropose;
                } else {
                    status = "COUNTER_OFFER";
                    message = "Le vendeur propose " + String.format("%.2f", nouveauPrix) + " MAD.";
                    prixAffiche = nouveauPrix;
                    accordTrouve = false;
                }

                state.status = status;
                state.roundActuel++;

                if (accordTrouve || isFinal || state.roundActuel > state.roundsMax) {
                    state.closed = true;
                }

                System.out.println("[MANUAL_NEGO] nouveauPrix=" + nouveauPrix);
                System.out.println("[MANUAL_NEGO] status=" + status);

                return ResponseEntity.ok(Map.of(
                    "mode", "MANUAL",
                    "status", status,
                    "message", message,
                    "prixPropose", prixPropose,
                    "prixVendeur", nouveauPrix,
                    "prixAffiche", prixAffiche,
                    "accordTrouve", accordTrouve,
                    "isFinalOffer", state.closed,
                    "roundActuel", Math.min(state.roundActuel, state.roundsMax),
                    "roundsMax", state.roundsMax
                ));
            }
        }
        
        System.out.println("[MANUAL_NEGO] status=ERROR");
        return ResponseEntity.ok(Map.of("status", "ERROR", "mode", "MANUAL", "message", "Erreur de communication avec le vendeur."));
    }

    @PostMapping("/securite/verifier")
    public ResponseEntity<?> verifierSecurite(@RequestBody Map<String, Object> request) {
        return contactAgent("AgentSecurite", ACLMessage.REQUEST, request);
    }

    // --- New Commentary & Navigation Endpoints ---

    @PostMapping("/acheteur/commenter")
    public ResponseEntity<?> commenterNegociation(@RequestBody Map<String, Object> request) {
        String behavior = (String) request.get("buyerBehavior");
        String trend = (String) request.get("buyerTrend");

        String response = kimiService.generateManualNegotiationAdvice(behavior, trend);
        return ResponseEntity.ok(Map.of("message", response));
    }

    @PostMapping("/chat/navigate")
    public ResponseEntity<?> chatNavigate(@RequestBody Map<String, Object> request) {
        String sessionId = (String) request.get("sessionId");
        String userMessage = (String) request.get("message");
        
        // Retrieve and format history for this session
        List<Map<String, String>> history = chatHistory.getOrDefault(sessionId, new ArrayList<>());
        
        // 1. Intent Detection
        String llmIntent = kimiService.detectNavigationIntent(
            SystemPrompts.chatNavigation(userMessage),
            userMessage, 
            history
        );
        Map<String, Object> intent = null;
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
            
            // Fix heuristic fallback
            String lower = userMessage.toLowerCase();
            boolean isSearchIntent =
                lower.contains("have")        || lower.contains("avez") ||
                lower.contains("disponible")  || lower.contains("available") ||
                lower.contains("veux")        || lower.contains("cherche") ||
                lower.contains("want")        || lower.contains("trouve") ||
                lower.contains("looking for") || lower.contains("find") ||
                lower.contains("got any")     || lower.contains("what about") ||
                lower.contains("and also")    || lower.contains("aussi") ||
                lower.contains("too")         || lower.contains("show me") ||
                lower.contains("offres")      || lower.contains("offers") ||
                lower.contains("gimme")       || lower.contains("give me") ||
                lower.contains("range")       || lower.contains("budget") ||
                lower.contains("price")       || lower.contains("sous") ||
                lower.contains("under")       || lower.contains("moins de");
            
            if (isSearchIntent) {
                String searchTerm = cleanProductSearchQuery(userMessage);
                if (searchTerm != null && !searchTerm.isBlank()) {
                    intent = new HashMap<>();
                    intent.put("intention", "SEARCH_PRODUCT");
                    intent.put("recherche", searchTerm);
                    intent.put("categorie", null);
                    intent.put("reponse", "Je recherche '" + searchTerm + "' pour vous !");
                }
            }
            
            // If not handled by heuristic, perform generic fallbacks
            if (intent == null) {
                if (llmIntent != null && llmIntent.trim().length() > 10 
                    && !llmIntent.contains("Exception")) {
                    String cleaned = llmIntent
                        .replaceAll("(?si)<think>.*?(</think>|$)", "")
                        .trim();
                    
                    if (!cleaned.startsWith("{")) {
                        return ResponseEntity.ok(Map.of("type", "GENERAL", "reponse", cleaned));
                    }
                }
                
                String lower2 = userMessage.toLowerCase();
                
                // Product-related keywords → create intent for product search (don't return early!)
                if (lower2.contains("iphone") || lower2.contains("laptop") || 
                    lower2.contains("téléphone") || lower2.contains("phone") ||
                    lower2.contains("samsung") || lower2.contains("ordinateur") ||
                    lower2.contains("ordinator") || lower2.contains("computer") ||
                    lower2.contains("produit") || lower2.contains("offers") ||
                    lower2.contains("offres") || lower2.contains("price") ||
                    lower2.contains("range") || lower2.contains("budget")) {
                    String searchTerm = cleanProductSearchQuery(userMessage);
                    if (searchTerm == null || searchTerm.isBlank()) searchTerm = "";
                    intent = new HashMap<>();
                    intent.put("intention", "SEARCH_PRODUCT");
                    intent.put("recherche", searchTerm);
                    intent.put("categorie", null);
                    intent.put("reponse", "Je recherche ça pour vous...");
                } else if (lower2.contains("commande") || lower2.contains("order") ||
                           lower2.contains("livraison") || lower2.contains("statut")) {
                    return ResponseEntity.ok(Map.of("type", "CHECK_ORDER", "reponse", "Je vérifie vos commandes..."));
                } else {
                    return ResponseEntity.ok(Map.of("type", "GENERAL", "reponse", "Bonjour ! Je peux vous aider à trouver des produits."));
                }
            }
        }

        String intention = intent.containsKey("intent") ? (String) intent.get("intent") : (String) intent.get("intention");
        if (intention == null) intention = "GENERAL";
        
        // Normalisation intent search
        if ("CHECK_PRODUCT_AVAILABILITY".equalsIgnoreCase(intention) || "SEARCH_PRODUCT".equalsIgnoreCase(intention)) {
            intention = "PRODUCT_SEARCH";
        }

        // Step 5, 7: Keyword purification & backend semantic normalization
        String rawSearchQuery = intent.containsKey("searchQuery") ? (String) intent.get("searchQuery") : (String) intent.get("recherche");
        String cleanedSearchQuery = cleanProductSearchQuery(rawSearchQuery);

        if (cleanedSearchQuery.isBlank()) {
            cleanedSearchQuery = cleanProductSearchQuery(userMessage);
        }

        // Enforce deterministic semantic normalize (ordinator -> ordinateur, iphoe -> iphone, etc)
        cleanedSearchQuery = normalizeProductKeyword(cleanedSearchQuery, userMessage);

        // Extra safety: If query is only numeric, clear it!
        if (cleanedSearchQuery != null && cleanedSearchQuery.matches("\\d+")) {
            cleanedSearchQuery = normalizeProductKeyword(null, userMessage);
            if (cleanedSearchQuery != null && cleanedSearchQuery.matches("\\d+")) {
                cleanedSearchQuery = "";
            }
        }

        String category = intent.containsKey("category") ? (String) intent.get("category") : (String) intent.get("categorie");
        String agentResponse = intent.containsKey("responseBeforeSearch") ? (String) intent.get("responseBeforeSearch") : (String) intent.get("reponse");
        String requestType = intent.containsKey("requestType") ? (String) intent.get("requestType") : "GENERAL";

        // Step 6: Deterministic Price extraction fallbacks
        Double priceMin = null;
        Double priceMax = null;
        try {
            if (intent.containsKey("priceMin") && intent.get("priceMin") != null) {
                priceMin = ((Number) intent.get("priceMin")).doubleValue();
            }
            if (intent.containsKey("priceMax") && intent.get("priceMax") != null) {
                priceMax = ((Number) intent.get("priceMax")).doubleValue();
            }
        } catch (Exception e) {
            System.err.println("[CHAT_NAVIGATE] Price parsing failure: " + e.getMessage());
        }

        // Backup extraction directly via backend regex for reliability
        Double backendPriceMax = extractPriceMax(userMessage);
        if (backendPriceMax != null) {
            priceMax = backendPriceMax;
        }

        Map<String, Object> result = new HashMap<>();
        result.put("type", intention);
        result.put("reponse", agentResponse);

        // Step 1: MANDATORY LOGGING
        System.out.println("[CHAT] userMessage=" + userMessage);
        System.out.println("[CHAT] llmRaw=" + llmIntent);
        System.out.println("[CHAT] parsedIntent=" + intent);
        System.out.println("[CHAT] rawSearchQuery=" + rawSearchQuery);
        System.out.println("[CHAT] cleanedSearchQuery=" + cleanedSearchQuery);
        System.out.println("[CHAT] category=" + category);
        System.out.println("[CHAT] priceMin=" + priceMin);
        System.out.println("[CHAT] priceMax=" + priceMax);

        // 2. Data Retrieval based on Intent
        if ("PRODUCT_SEARCH".equals(intention) || "VIEW_CATEGORY".equals(intention)) {
            try {
                // Forward JWT Token
                HttpHeaders headers = new HttpHeaders();
                ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
                if (attrs != null) {
                    String authHeader = attrs.getRequest().getHeader("Authorization");
                    if (authHeader != null) headers.set("Authorization", authHeader);
                }
                
                HttpEntity<String> entity = new HttpEntity<>(headers);
                List<Map<String, Object>> all = new ArrayList<>();
                String finalQueryUrlUsed = "";
                int finalHttpStatus = 0;

                // STEP A: Search by cleanedSearchQuery ONLY
                if (cleanedSearchQuery != null && !cleanedSearchQuery.isBlank()) {
                    StringBuilder urlBuilder = new StringBuilder(PRODUCT_SERVICE_URL + "/products?");
                    urlBuilder.append("search=").append(java.net.URLEncoder.encode(cleanedSearchQuery, "UTF-8")).append("&");
                    if (priceMin != null) urlBuilder.append("priceMin=").append(priceMin).append("&");
                    if (priceMax != null) urlBuilder.append("priceMax=").append(priceMax).append("&");
                    
                    String url = urlBuilder.toString();
                    if (url.endsWith("&") || url.endsWith("?")) url = url.substring(0, url.length() - 1);
                    finalQueryUrlUsed = url;

                    ResponseEntity<List> res = externalRestTemplate.exchange(url, org.springframework.http.HttpMethod.GET, entity, List.class);
                    finalHttpStatus = res.getStatusCode().value();
                    if (res.getStatusCode().is2xxSuccessful() && res.getBody() != null) {
                        all = (List<Map<String, Object>>) res.getBody();
                    }
                }

                // STEP B: If empty & category exists
                if (all.isEmpty() && category != null && !category.isBlank()) {
                    StringBuilder urlBuilder = new StringBuilder(PRODUCT_SERVICE_URL + "/products?");
                    urlBuilder.append("category=").append(java.net.URLEncoder.encode(category, "UTF-8")).append("&");
                    if (priceMin != null) urlBuilder.append("priceMin=").append(priceMin).append("&");
                    if (priceMax != null) urlBuilder.append("priceMax=").append(priceMax).append("&");
                    
                    String url = urlBuilder.toString();
                    if (url.endsWith("&") || url.endsWith("?")) url = url.substring(0, url.length() - 1);
                    finalQueryUrlUsed = url;

                    ResponseEntity<List> res = externalRestTemplate.exchange(url, org.springframework.http.HttpMethod.GET, entity, List.class);
                    finalHttpStatus = res.getStatusCode().value();
                    if (res.getStatusCode().is2xxSuccessful() && res.getBody() != null) {
                        all = (List<Map<String, Object>>) res.getBody();
                    }
                }

                // STEP C removed — returning the full catalog without any text filter
                // was causing irrelevant products to appear. If A and B returned nothing,
                // we go straight to fuzzy matching below.

                System.out.println("[CHAT] productServiceUrl=" + finalQueryUrlUsed);
                System.out.println("[CHAT] productServiceStatus=" + finalHttpStatus);
                System.out.println("[CHAT] productsFound=" + all.size());

                // Language Detection
                String lowerMsg = userMessage.toLowerCase();
                boolean isEnglish = lowerMsg.matches(".*\\b(have|any|in|stock|available|do|you|u|find|show|about|where|offers|gimme|give)\\b.*");
                String finalSearchQuery = (cleanedSearchQuery != null && !cleanedSearchQuery.isEmpty()) ? cleanedSearchQuery : "ce produit";

                if (all.isEmpty()) {
                    boolean fuzzyMatched = false;

                    // Fuzzy matching fallback locally
                    if (cleanedSearchQuery != null && !cleanedSearchQuery.isEmpty() && cleanedSearchQuery.length() >= 3) {
                        try {
                            ResponseEntity<List> catalogRes = externalRestTemplate.exchange(PRODUCT_SERVICE_URL + "/products", org.springframework.http.HttpMethod.GET, entity, List.class);
                            if (catalogRes.getStatusCode().is2xxSuccessful() && catalogRes.getBody() != null) {
                                List<Map<String, Object>> catalog = (List<Map<String, Object>>) catalogRes.getBody();
                                
                                Map<String, Object> bestMatch = null;
                                double bestSim = 0.0;
                                
                                for (Map<String, Object> p : catalog) {
                                    String title = (String) p.get("titre");
                                    if (title != null) {
                                        double sim = getSimilarity(cleanedSearchQuery, title.trim());
                                        if (sim > bestSim) {
                                            bestSim = sim;
                                            bestMatch = p;
                                        }
                                    }
                                }
                                
                                if (bestMatch != null && bestSim >= 0.75) {
                                    String suggestedTitle = (String) bestMatch.get("titre");
                                    result.put("type", "PRODUCTS_FOUND");
                                    
                                    String finalResp = isEnglish
                                        ? String.format("I couldn’t find “%s”. Did you mean “%s”?", cleanedSearchQuery, suggestedTitle)
                                        : String.format("Je n’ai pas trouvé « %s ». Vouliez-vous dire « %s » ?", cleanedSearchQuery, suggestedTitle);
                                    
                                    result.put("reponse", finalResp);
                                    
                                    Map<String, Object> m = new HashMap<>();
                                    m.put("id", bestMatch.get("id").toString());
                                    m.put("titre", bestMatch.get("titre"));
                                    m.put("prix", bestMatch.get("prix"));
                                    m.put("imageUrl", bestMatch.get("imageUrl"));
                                    m.put("categorie", bestMatch.get("categorie"));
                                    
                                    result.put("produits", List.of(m));
                                    fuzzyMatched = true;
                                }
                            }
                        } catch (Exception fe) {
                            System.err.println("[CHAT_NAVIGATE] Fuzzy match failure: " + fe.getMessage());
                        }
                    }

                    if (!fuzzyMatched) {
                        // Step 8: Backend failure phrasing based on actual queries
                        result.put("type", "NO_PRODUCTS_FOUND");
                        String finalResp;
                        if (priceMax != null) {
                            finalResp = isEnglish
                                ? String.format("I couldn’t find available products matching “%s” within %.0f MAD right now.", finalSearchQuery, priceMax)
                                : String.format("Je n’ai trouvé aucun produit disponible « %s » dans votre budget de %.0f MAD pour le moment.", finalSearchQuery, priceMax);
                        } else {
                            finalResp = isEnglish
                                ? String.format("I couldn’t find available products matching “%s” right now.", finalSearchQuery)
                                : String.format("Je n’ai trouvé aucun produit disponible correspondant à « %s » pour le moment.", finalSearchQuery);
                        }
                        result.put("reponse", finalResp);
                        result.put("produits", new ArrayList<>());
                    }
                } else {
                    // Check overall stock count sum
                    int totalStock = 0;
                    for (Map<String, Object> p : all) {
                        if (p.containsKey("stock") && p.get("stock") != null) {
                            totalStock += ((Number) p.get("stock")).intValue();
                        } else {
                            totalStock += 1;
                        }
                    }

                    if (totalStock <= 0) {
                        result.put("type", "NO_PRODUCTS_FOUND");
                        String finalResp = isEnglish
                            ? "The product exists, but it does not appear to be available in stock right now."
                            : "Le produit existe, mais il ne semble pas être disponible en stock pour le moment.";
                        result.put("reponse", finalResp);
                        result.put("produits", new ArrayList<>());
                    } else {
                        result.put("type", "PRODUCTS_FOUND");
                        
                        // Step 8: Adapted response phrasing for budget matching!
                        String finalResp;
                        if ("OFFERS".equalsIgnoreCase(requestType)) {
                            finalResp = isEnglish
                                ? String.format("Here are the available offers/products matching “%s”.", finalSearchQuery)
                                : String.format("Voici les offres ou produits disponibles correspondant à « %s ».", finalSearchQuery);
                        } else if (priceMax != null) {
                            finalResp = isEnglish
                                ? String.format("Yes, I found products matching “%s” within your %.0f MAD budget.", finalSearchQuery, priceMax)
                                : String.format("Oui, j'ai trouvé des produits « %s » correspondant à votre budget de %.0f MAD.", finalSearchQuery, priceMax);
                        } else {
                            finalResp = isEnglish
                                ? String.format("Yes, I found products matching “%s”.", finalSearchQuery)
                                : String.format("Oui, j’ai trouvé des produits correspondant à « %s ».", finalSearchQuery);
                        }
                        
                        result.put("reponse", finalResp);
                        
                        // Map to mini cards (Limit 3)
                        List<Map<String, Object>> clean = all.stream()
                            .filter(p -> !p.containsKey("stock") || p.get("stock") == null || ((Number) p.get("stock")).intValue() > 0)
                            .limit(3)
                            .map(p -> {
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
                }
            } catch (Exception e) {
                System.err.println("[CHAT_NAVIGATE] Product fetch error for intent: " + intention + " | Error: " + e.getMessage());
                result.put("type", "NO_PRODUCTS_FOUND");
                result.put("reponse", "Une erreur est survenue lors de la recherche.");
                result.put("produits", new ArrayList<>());
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
        
        // Update History AFTER calculations to save ground-truth response
        String finalWrittenResponse = (String) result.get("reponse");
        history.add(Map.of("role", "user", "content", userMessage));
        history.add(Map.of("role", "assistant", "content", finalWrittenResponse != null ? finalWrittenResponse : ""));
        if (history.size() > 10) {
            history = history.subList(history.size() - 10, history.size());
        }
        chatHistory.put(sessionId, history);

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

    @PostMapping("/nego/auto/start")
    public ResponseEntity<?> autoNegoStart(@RequestBody Map<String, Object> request) {
        String negoId = (String) request.get("negociationId");
        double prixCibleRaw = ((Number) request.get("budget")).doubleValue(); // Changed from prixCible to budget to match spec payload but accept both
        if (prixCibleRaw == 0 && request.containsKey("prixCible")) {
            prixCibleRaw = ((Number) request.get("prixCible")).doubleValue();
        }
        
        final double prixCible = prixCibleRaw;
        
        double prixPlancher = ((Number) request.get("prixMin")).doubleValue();
        double pActuel = (request.get("prixActuel") instanceof Number) ? ((Number) request.get("prixActuel")).doubleValue() : 0.0;
        int roundsMax = (request.get("roundsMax") instanceof Number) ? ((Number) request.get("roundsMax")).intValue() : 5;
        double prixInitial = (request.get("prixInitial") instanceof Number) ? ((Number) request.get("prixInitial")).doubleValue() : pActuel;

        System.out.println("[AUTO_NEGO] negociationId=" + negoId);
        System.out.println("[AUTO_NEGO] budget=" + prixCible);
        System.out.println("[AUTO_NEGO] prixMin=" + prixPlancher);

        AutoNegotiationState state = autoStateMap.computeIfAbsent(negoId, k -> 
            new AutoNegotiationState(negoId, prixInitial, prixPlancher, prixCible, roundsMax)
        );

        if (state.autoInProgress) {
            return ResponseEntity.ok(Map.of(
                "mode", "AUTO",
                "status", "ERROR",
                "message", "Une négociation automatique est déjà en cours."
            ));
        }

        if (state.closed && "ACCEPTED".equals(state.status)) {
            return ResponseEntity.ok(Map.of(
                "mode", "AUTO",
                "status", "ACCEPTED",
                "message", "Un accord a déjà été trouvé pour cette négociation."
            ));
        }

        if (state.closed && "NO_AGREEMENT".equals(state.status)) {
            return ResponseEntity.ok(Map.of(
                "mode", "AUTO",
                "status", "NO_AGREEMENT",
                "message", "La négociation automatique est déjà terminée sans accord. Vous pouvez continuer manuellement ou augmenter votre budget."
            ));
        }

        state.autoInProgress = true;

        if (prixCible < prixPlancher) {
            state.autoInProgress = false;
            state.closed = true;
            state.status = "INVALID_BUDGET";
            System.out.println("[AUTO_NEGO] status=INVALID_BUDGET (budget < prixMin)");
            return ResponseEntity.ok(Map.of(
                "mode", "AUTO",
                "status", "INVALID_BUDGET",
                "message", "Votre budget est inférieur au prix minimum acceptable. Aucun accord automatique n'est possible.",
                "budget", prixCible,
                "accordTrouve", false,
                "roundsUsed", 0
            ));
        }

        double derniereOffre = 0;
        double prixActuelCourant = pActuel; // Assuming auto starts from current visible price
        double prixFinal = prixActuelCourant;
        String lastBuyerTrend = "STABLE";
        List<Double> historiqueOffres = new ArrayList<>();
        boolean accordTrouve = false;

        for (int round = 1; round <= roundsMax; round++) {
            state.roundsUsed = round;

            double offreAcheteur = com.auramarket.agents.strategy.BuyerNegotiationStrategy.calculateNextOffer(
                prixCible, prixActuelCourant, lastBuyerTrend, round, derniereOffre
            );

            System.out.println("[AUTO_NEGO] round=" + round + " buyerOffer=" + offreAcheteur);

            Map<String, Object> negoPayload = new HashMap<>();
            negoPayload.put("negociationId", negoId + "_auto"); // Isolated from manual JADE state
            negoPayload.put("prixActuel",    prixActuelCourant);
            negoPayload.put("prixMin",       prixPlancher);
            negoPayload.put("prixPropose",   offreAcheteur);
            negoPayload.put("roundActuel",   round);
            negoPayload.put("roundsMax",     roundsMax);
            negoPayload.put("historiqueOffres", historiqueOffres);

            ResponseEntity<?> negoResponse = contactAgent("AgentNegociation", ACLMessage.PROPOSE, negoPayload);

            if (negoResponse.getStatusCode() != HttpStatus.OK || negoResponse.getBody() == null) {
                System.err.println("[AUTO_NEGO] Échec de communication avec AgentNegociation");
                state.autoInProgress = false;
                return ResponseEntity.ok(Map.of("status", "ERROR", "mode", "AUTO", "message", "Erreur de communication."));
            }

            @SuppressWarnings("unchecked")
            Map<String, Object> result = (Map<String, Object>) negoResponse.getBody();
            double nouveauPrix = ((Number) result.get("nouveauPrix")).doubleValue();
            boolean isFinalOffer = (Boolean) result.getOrDefault("isFinalOffer", false);
            lastBuyerTrend = (String) result.getOrDefault("buyerTrend", "STABLE");
            String buyerBehavior = (String) result.getOrDefault("buyerBehavior", "NORMAL");

            System.out.println("[AUTO_NEGO] round=" + round + " sellerResponse=" + nouveauPrix);

            state.trace.add(new AutoRoundTrace(round, offreAcheteur, nouveauPrix, buyerBehavior, lastBuyerTrend));
            historiqueOffres.add(offreAcheteur);
            
            prixActuelCourant = nouveauPrix;
            derniereOffre = offreAcheteur;
            prixFinal = nouveauPrix;

            if (nouveauPrix <= prixCible) {
                accordTrouve = true;
                break;
            }

            if (isFinalOffer) {
                break;
            }
        }

        state.autoInProgress = false;
        state.closed = true;
        state.lastUpdated = System.currentTimeMillis();

        if (accordTrouve) {
            state.status = "ACCEPTED";
            System.out.println("[AUTO_NEGO] status=ACCEPTED");
            return ResponseEntity.ok(Map.of(
                "mode", "AUTO",
                "status", "ACCEPTED",
                "message", "🎉 Accord trouvé automatiquement ! Prix final : " + String.format("%.2f", prixFinal) + " MAD.",
                "budget", prixCible,
                "prixFinal", prixFinal,
                "accordTrouve", true,
                "roundsUsed", state.roundsUsed,
                "trace", state.trace
            ));
        } else {
            state.status = "NO_AGREEMENT";
            System.out.println("[AUTO_NEGO] status=NO_AGREEMENT");
            return ResponseEntity.ok(Map.of(
                "mode", "AUTO",
                "status", "NO_AGREEMENT",
                "message", "Aucun accord automatique n'a pu être trouvé dans votre budget. Dernière proposition du vendeur : " + String.format("%.2f", prixFinal) + " MAD.",
                "budget", prixCible,
                "prixFinal", prixFinal,
                "accordTrouve", false,
                "roundsUsed", state.roundsUsed,
                "trace", state.trace
            ));
        }
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
                errorReporter.reportTimeout("agents-bridge", agentName, 300000);
                return ResponseEntity.status(HttpStatus.REQUEST_TIMEOUT)
                        .body(Map.of("error", "Agent " + agentName + " timed out"));
            }

            return ResponseEntity.ok(mapper.readValue(agentReply[0], Map.class));

        } catch (Exception e) {
            errorReporter.reportJadeError("agents-bridge", "Bridge Communication Crash: " + e.getMessage(), e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "Bridge Communication Error: " + e.getMessage()));
        }
    }

    private String cleanProductSearchQuery(String input) {
        if (input == null) return "";

        String q = input.toLowerCase().trim();

        // Request phrases (EN, FR, Darija)
        q = q.replaceAll("\\bdo you have\\b", "");
        q = q.replaceAll("\\bdo u have\\b", "");
        q = q.replaceAll("\\bdo you sell\\b", "");
        q = q.replaceAll("\\bis there\\b", "");
        q = q.replaceAll("\\bgimme\\b", "");
        q = q.replaceAll("\\bgive me\\b", "");
        q = q.replaceAll("\\bshow me\\b", "");
        q = q.replaceAll("\\bshow\\b", "");
        q = q.replaceAll("\\bfind\\b", "");
        q = q.replaceAll("\\bsearch\\b", "");
        q = q.replaceAll("\\best ce que vous avez\\b", "");
        q = q.replaceAll("\\best-ce que vous avez\\b", "");
        q = q.replaceAll("\\bvous avez\\b", "");
        q = q.replaceAll("\\bje cherche\\b", "");
        q = q.replaceAll("\\bmontre moi\\b", "");
        q = q.replaceAll("\\bdonne moi\\b", "");
        q = q.replaceAll("\\bwach kayn\\b", "");
        q = q.replaceAll("\\bkayn\\b", "");

        // Availability words
        q = q.replaceAll("\\bavailable\\b", "");
        q = q.replaceAll("\\bdisponible\\b", "");
        q = q.replaceAll("\\bin stock\\b", "");
        q = q.replaceAll("\\bstock\\b", "");
        q = q.replaceAll("\\boffers\\b", "");
        q = q.replaceAll("\\boffres\\b", "");
        q = q.replaceAll("\\boffer\\b", "");
        q = q.replaceAll("\\bproducts\\b", "");
        q = q.replaceAll("\\bproduct\\b", "");
        q = q.replaceAll("\\bplease\\b", "");
        q = q.replaceAll("\\bfor me\\b", "");

        // Price/range noise (MUST come before generic word removal)
        q = q.replaceAll("\\bin the range of the price of\\b", "");
        q = q.replaceAll("\\brange of the price of\\b", "");
        q = q.replaceAll("\\bin the range of\\b", "");
        q = q.replaceAll("\\bin range of\\b", "");
        q = q.replaceAll("\\bin range price\\b", "");
        q = q.replaceAll("\\brange of\\b", "");
        q = q.replaceAll("\\brange\\b", "");
        q = q.replaceAll("\\bprice\\b", "");
        q = q.replaceAll("\\bunder\\b", "");
        q = q.replaceAll("\\bless than\\b", "");
        q = q.replaceAll("\\bmoins de\\b", "");
        q = q.replaceAll("\\bbudget\\b", "");
        q = q.replaceAll("\\baround\\b", "");
        q = q.replaceAll("\\benviron\\b", "");
        q = q.replaceAll("\\bmax\\b", "");

        // Currency
        q = q.replaceAll("\\d+\\s*mad\\b", "");
        q = q.replaceAll("\\d+\\s*dh\\b", "");
        q = q.replaceAll("\\bmad\\b", "");
        q = q.replaceAll("\\bdh\\b", "");

        // Generic filler words
        q = q.replaceAll("\\bof\\b", "");
        q = q.replaceAll("\\bthe\\b", "");
        q = q.replaceAll("\\ban\\b", "");
        q = q.replaceAll("\\ba\\b", "");
        q = q.replaceAll("\\bin\\b", "");
        q = q.replaceAll("\\blast\\b", "");
        q = q.replaceAll("\\bdes\\b", "");
        q = q.replaceAll("\\bles\\b", "");
        q = q.replaceAll("\\bun\\b", "");
        q = q.replaceAll("\\bune\\b", "");

        // Remove standalone numbers (prices already captured by extractPriceMax)
        q = q.replaceAll("\\b\\d+\\b", "");

        // Cleanup
        q = q.replaceAll("[?!.,;:]", " ");
        q = q.replaceAll("\\s+", " ").trim();

        return q;
    }

    private Double extractPriceMax(String message) {
        if (message == null) return null;

        String lower = message.toLowerCase();

        Pattern p = Pattern.compile("(\\d{3,7})\\s*(mad|dh)?");
        Matcher m = p.matcher(lower);

        if (m.find()) {
            double value = Double.parseDouble(m.group(1));

            if (lower.contains("under")
                || lower.contains("less than")
                || lower.contains("moins de")
                || lower.contains("max")
                || lower.contains("budget")
                || lower.contains("range of the price")
                || lower.contains("range")) {
                return value;
            }
        }

        return null;
    }

    private String normalizeProductKeyword(String query, String originalMessage) {
        String combined = ((query == null ? "" : query) + " " + originalMessage).toLowerCase();

        // Computer family — check BEFORE phone ("pc" is a substring)
        if (combined.contains("ordinator") || combined.contains("ordinateur")
            || combined.contains("computer") || combined.contains("laptop")
            || combined.contains("notebook") || combined.contains("portable")
            || combined.matches(".*\\bpc\\b.*") || combined.matches(".*\\bpc gamer\\b.*")) {
            return "ordinateur";
        }

        // iPhone specifically (before generic phone)
        if (combined.contains("iphoe") || combined.contains("iphone")
            || combined.contains("apple phone") || combined.contains("i phone")) {
            return "iphone";
        }

        // Generic phone / téléphone
        if (combined.matches(".*\\bphone\\b.*") || combined.matches(".*\\bphones\\b.*")
            || combined.contains("telephone") || combined.contains("téléphone")
            || combined.contains("smartphone") || combined.contains("mobile")) {
            return "telephone";
        }

        if (combined.contains("samsung") || combined.contains("galaxy")) {
            return "samsung";
        }

        // Shoes
        if (combined.contains("sneaker") || combined.contains("basket")
            || combined.matches(".*\\bshoe\\b.*") || combined.matches(".*\\bshoes\\b.*")) {
            return "chaussures";
        }

        return query;
    }

    private int levenshteinDistance(CharSequence lhs, CharSequence rhs) {
        int len0 = lhs.length() + 1;
        int len1 = rhs.length() + 1;
        int[] cost = new int[len0];
        int[] newcost = new int[len0];
        for (int i = 0; i < len0; i++) cost[i] = i;
        for (int j = 1; j < len1; j++) {
            newcost[0] = j;
            for (int i = 1; i < len0; i++) {
                int match = (Character.toLowerCase(lhs.charAt(i - 1)) == Character.toLowerCase(rhs.charAt(j - 1))) ? 0 : 1;
                int cost_replace = cost[i - 1] + match;
                int cost_insert = cost[i] + 1;
                int cost_delete = newcost[i - 1] + 1;
                newcost[i] = Math.min(Math.min(cost_insert, cost_delete), cost_replace);
            }
            int[] swap = cost; cost = newcost; newcost = swap;
        }
        return cost[len0 - 1];
    }

    private double getSimilarity(String s1, String s2) {
        if (s1 == null || s2 == null) return 0.0;
        int dist = levenshteinDistance(s1, s2);
        int maxLen = Math.max(s1.length(), s2.length());
        if (maxLen == 0) return 1.0;
        return 1.0 - ((double) dist / maxLen);
    }
}
