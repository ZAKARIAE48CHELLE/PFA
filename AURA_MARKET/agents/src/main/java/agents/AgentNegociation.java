package agents;

import jade.core.Agent;
import jade.core.behaviours.CyclicBehaviour;
import jade.lang.acl.ACLMessage;
import com.fasterxml.jackson.databind.ObjectMapper;
import net.sourceforge.jFuzzyLogic.FIS;

import java.io.InputStream;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestTemplate;

/**
 * AgentNegociation — Version FINALE + Renforcement
 *
 * Représente le VENDEUR dans une négociation de prix.
 * Utilise la logique floue (jFuzzyLogic) + un système de renforcement
 * basé sur l'historique pour forcer la convergence vers un accord.
 */
public class AgentNegociation extends Agent {

    private final ObjectMapper mapper = new ObjectMapper();
    private FIS fis;
    private com.auramarket.agents.service.KimiService kimi;
    private final RestTemplate restTemplate = new RestTemplate();

    private void reportError(String type, String msg, String severity) {
        try {
            Map<String, Object> dto = new HashMap<>();
            dto.put("service", "JADE-AgentNegociation");
            dto.put("errorType", type);
            dto.put("message", msg);
            dto.put("severity", severity != null ? severity : "HIGH");
            
            HttpHeaders h = new HttpHeaders();
            h.setContentType(MediaType.APPLICATION_JSON);
            restTemplate.postForEntity("http://audit-service:8084/audits/errors", new HttpEntity<>(dto, h), Map.class);
        } catch (Exception ignored) {}
    }

    @Override
    protected void setup() {
        Object[] args = getArguments();
        if (args != null && args.length > 0 && args[0] instanceof com.auramarket.agents.service.KimiService) {
            this.kimi = (com.auramarket.agents.service.KimiService) args[0];
            System.out.println("[AgentNegociation] KimiService injecté.");
        }
        
        System.out.println("[AgentNegociation] Démarrage : " + getLocalName());
        loadFuzzyEngine();

        addBehaviour(new CyclicBehaviour() {
            @Override
            public void action() {
                ACLMessage msg = receive();
                if (msg != null) {
                    try {
                        Map<String, Object> input = mapper.readValue(msg.getContent(), Map.class);
                        Map<String, Object> response = processNegotiation(input);

                        ACLMessage reply = msg.createReply();
                        reply.setPerformative(ACLMessage.INFORM);
                        reply.setContent(mapper.writeValueAsString(response));
                        send(reply);

                    } catch (Exception e) {
                        System.err.println("[AgentNegociation] Erreur : " + e.getMessage());
                        reportError("NEGO_ERROR", "Negociation process crashed: " + e.getMessage(), "HIGH");
                        e.printStackTrace();
                        try {
                            ACLMessage reply = msg.createReply();
                            reply.setPerformative(ACLMessage.FAILURE);
                            reply.setContent("{\"error\":\"" + e.getMessage() + "\"}");
                            send(reply);
                        } catch (Exception ex) { ex.printStackTrace(); }
                    }
                } else {
                    block();
                }
            }
        });
    }

    private void loadFuzzyEngine() {
        System.out.println("[FCL] Chargement de negotiation.fcl...");
        try {
            InputStream stream = getClass().getResourceAsStream("/negotiation.fcl");
            if (stream == null) {
                System.err.println("[FCL ERROR] negotiation.fcl introuvable.");
                return;
            }
            fis = FIS.load(stream, true);
            System.out.println(fis != null ? "[FCL] Chargé avec succès." : "[FCL ERROR] Parsing échoué.");
        } catch (Exception e) {
            System.err.println("[FCL ERROR] " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> processNegotiation(Map<String, Object> input) {

        String negociationId    = (String) input.get("negociationId");
        double prixActuel       = toDouble(input.get("prixActuel"));
        double prixPlancher     = toDouble(input.get("prixMin"));
        double prixPropose      = toDouble(input.get("prixPropose"));
        int    roundActuel      = toInt(input.get("roundActuel"));
        int    roundsMax        = toInt(input.get("roundsMax"));
        List<Number> historique = (List<Number>) input.get("historiqueOffres");
        double epsilon = 0.05;

        System.out.println("\n[AgentNegociation] ══════════════════════════════════");
        System.out.println("[AgentNegociation] Round " + roundActuel + "/" + roundsMax);
        System.out.println("[AgentNegociation] prixActuel=" + prixActuel
                + " | prixPlancher=" + prixPlancher + " | prixPropose=" + prixPropose);

        // ── GARDE 0 : Config invalide ─────────────────────────────────────────
        if (prixPlancher <= 0 || prixPlancher > prixActuel + epsilon) {
            System.err.println("[GUARD 0b] prixPlancher invalide : " + prixPlancher + " (prixActuel=" + prixActuel + ")");
            return build(negociationId, prixActuel, 0, "INVALID_CONFIG", "STABLE", roundActuel, true);
        }

        // ── GARDE 5 : Acheteur au-dessus du prix actuel ──────────────────────
        // On accepte toujours si l'acheteur propose plus que ce qu'on demande !
        if (prixPropose >= prixActuel - epsilon) {
            System.out.println("[GUARD 5] prixPropose >= prixActuel → acceptation immédiate");
            return build(negociationId, prixPropose, 0, "ACCEPTED", "IMPROVING", roundActuel, true);
        }

        // ── GARDE 1 : Dépassement rounds ─────────────────────────────────────
        if (roundActuel > roundsMax) {
            System.err.println("[GUARD 1] Dépassement roundsMax — clôture forcée");
            return build(negociationId, prixPlancher, prixActuel - prixPlancher, "TIMEOUT", "STABLE", roundActuel, true);
        }

        // ── GARDE 2 : Offre invalide ──────────────────────────────────────────
        if (prixPropose <= 0) {
            System.err.println("[GUARD 2] prixPropose invalide : " + prixPropose);
            return build(negociationId, prixActuel, 0, "INVALID", "STABLE", roundActuel, false);
        }

        // ── GARDE 3 : Sous le plancher ────────────────────────────────────────
        if (prixPropose < prixPlancher - epsilon) {
            System.out.println("[GUARD 3] Offre sous plancher → vendeur immobile");
            return build(negociationId, prixActuel, 0,
                         "AGGRESSIVE_BUYER", "DECLINING", roundActuel, false);
            // isFinalOffer = false → laisse l'acheteur faire une meilleure offre
        }

        // ── GARDE 4 : Au plancher (avec epsilon) ──────────────────────────────
        if (prixPropose <= prixPlancher + epsilon) {
            System.out.println("[GUARD 4] Au plancher → acceptation immédiate");
            return build(negociationId, prixPlancher, prixActuel - prixPlancher, "ACCEPTED_AT_FLOOR", "IMPROVING", roundActuel, true);
        }

        // ── GARDE 4b : Marge résiduelle nulle ────────────────────────────────
        if (prixActuel - prixPlancher <= epsilon) {
            System.out.println("[GUARD 4b] Marge résiduelle nulle → attente acheteur sur prixPlancher=" + prixPlancher);
            return build(negociationId, prixPlancher, 0, "FLOOR_REACHED", "STABLE", roundActuel, (roundActuel >= roundsMax));
        }


        // ── ÉTAPE 0 : Kimi Inference (Si disponible) ─────────────────────────
        // [DÉSACTIVÉ] L'appel au LLM ici provoque une latence massive (5 rounds * 50s = timeout).
        // La logique floue (Fuzzy Logic) en Étape 1+ est beaucoup plus rapide et mathématiquement stable.
        /*
        if (kimi != null) {
            Map<String, Object> kimiResult = runKimiSellerInference(prixActuel, prixPlancher, prixPropose, roundActuel, roundsMax, historique);
            if (kimiResult != null) {
                // ...
            }
        }
        */

        // ── ÉTAPE 1 : Variables fuzzy ─────────────────────────────────────────
        double ecart       = (prixActuel - prixPropose) / prixActuel * 100.0;
        double progression = (double) roundActuel / roundsMax;
        double tendance    = computeTrend(historique, prixActuel);

        String buyerBehavior = deriveBehavior(ecart);
        String buyerTrend    = deriveTrend(tendance);

        // ── ÉTAPE 2 : Fuzzy inference ─────────────────────────────────────────
        double concessionRate = runFuzzyInference(ecart, progression, tendance);

        // ── ÉTAPE 3 : Renforcement comportemental ─────────────────────────────
        double reinforcementBonus = computeReinforcementBonus(historique, prixActuel);

        // ── ÉTAPE 4 : Stagnation bonus ────────────────────────────────────────
        double stagnationBonus = computeStagnationBonus(historique);

        // Taux final = fuzzy + renforcement + stagnation
        concessionRate = concessionRate + reinforcementBonus + stagnationBonus;

        // FIX: Minimum 12% de concession
        // Sur grande marge → concéder moins en % pour garder une négociation progressive
        double margeAbsolue = prixActuel - prixPlancher;
        double minRate;
        if      (margeAbsolue > 2000) minRate = 0.04;  // grande marge
        else if (margeAbsolue > 1000) minRate = 0.06;  // marge moyenne
        else if (margeAbsolue > 500)  minRate = 0.08;  // petite marge
        else                          minRate = 0.12;  // très petite marge

        concessionRate = Math.max(minRate, concessionRate);

        // Max aussi adaptatif
        double maxRate;
        if      (margeAbsolue > 2000) maxRate = 0.08;
        else if (margeAbsolue > 1000) maxRate = 0.12;
        else if (margeAbsolue > 500)  maxRate = 0.18;
        else                          maxRate = 0.25;

        concessionRate = Math.min(maxRate, concessionRate);

        // ── ÉTAPE 5 : Calcul concession ───────────────────────────────────────
        double marge      = prixActuel - prixPlancher;
        double concession = concessionRate * marge;
        double candidat   = prixActuel - concession;
        
        // Si c'est l'avant dernier ou dernier round, on s'approche agressivement du min
        // Convergence progressive
        if (roundActuel >= roundsMax - 1) {
            // Dernier round : proposer mi-chemin entre prixActuel et prixPlancher au lieu du plancher direct
            double targetFinal = prixPlancher + (marge * 0.25);
            candidat = Math.min(candidat, targetFinal);
            System.out.println("[FINAL ROUND] convergence vers " + round2(targetFinal));
        }

        // Uniquement au tout dernier round → prixPlancher
        if (roundActuel >= roundsMax) {
            candidat = prixPlancher;
        }

        // ── ÉTAPE 6 : Protection vendeur (Stubbornness) ───────────────────────
        if (candidat <= prixPropose) {
            // Le vendeur ne concède que 25% de l'écart au lieu de 50%
            candidat = prixActuel - (prixActuel - prixPropose) * 0.25;
            candidat = Math.max(prixPlancher, candidat);
        }
        
        System.out.println("[DEBUG] concessionRate=" + concessionRate + " | marge=" + marge + " | candidat=" + candidat);

        // ── SEUIL DE CONVERGENCE AUTOMATIQUE ──────────────────────────────────
        double margeInitiale = prixActuel - prixPlancher;
        double ecartRestant = candidat - prixPropose;
        
        if (margeInitiale > 0) {
            double ecartRelatif = ecartRestant / margeInitiale;

            // Si l'écart restant est < 5% de la marge initiale → accepter
            if (ecartRelatif > 0 && ecartRelatif < 0.05) {
                System.out.println("[CONVERGENCE] Écart résiduel " 
                    + round2(ecartRelatif * 100) + "% < 5% → acceptation");
                return build(negociationId, prixPropose, prixActuel - prixPropose,
                             "ACCEPTED", "IMPROVING", roundActuel, true);
            }
        }

        // Si l'écart absolu est < 10 MAD et prixPropose > prixPlancher → accepter
        if (ecartRestant > 0 && ecartRestant < 10.0 && prixPropose > prixPlancher) {
            System.out.println("[CONVERGENCE] Écart absolu " 
                + round2(ecartRestant) + " MAD < 10 MAD → acceptation");
            return build(negociationId, prixPropose, prixActuel - prixPropose,
                         "ACCEPTED", "IMPROVING", roundActuel, true);
        }

        // ── ÉTAPE 7 : Clamp absolu ────────────────────────────────────────────
        double nouveauPrix = candidat;
        nouveauPrix = Math.max(prixPlancher, nouveauPrix);
        nouveauPrix = Math.max(prixPropose, nouveauPrix);
        nouveauPrix = Math.min(prixActuel, nouveauPrix);

        // ── ÉTAPE 8 : Détection blocage ───────────────────────────────────────
        boolean isFinalOffer = (nouveauPrix >= prixActuel);

        return build(negociationId, nouveauPrix, prixActuel - nouveauPrix,
                buyerBehavior, buyerTrend, roundActuel, isFinalOffer);
    }

    private double computeReinforcementBonus(List<Number> historique, double prixActuel) {
        if (historique == null || historique.size() < 2) return 0.0;
        double score = 0.0;
        for (int i = 1; i < historique.size(); i++) {
            double prev = historique.get(i - 1).doubleValue();
            double curr = historique.get(i).doubleValue();
            double delta = curr - prev;
            if (delta > prixActuel * 0.001) score += 0.05;
            else if (Math.abs(delta) <= prixActuel * 0.001) score -= 0.02;
            else score -= 0.04;
        }
        return Math.max(-0.15, Math.min(0.15, score));
    }

    private double computeStagnationBonus(List<Number> historique) {
        int repetitions = countRepetitions(historique);
        if (repetitions < 3) return 0.0;
        return Math.min(0.20, (repetitions - 2) * 0.05);
    }

    private int countRepetitions(List<Number> historique) {
        if (historique == null || historique.size() < 2) return 0;
        double lastOffer = historique.get(historique.size() - 1).doubleValue();
        int count = 1;
        for (int i = historique.size() - 2; i >= 0; i--) {
            if (Math.abs(historique.get(i).doubleValue() - lastOffer) < 0.01) count++;
            else break;
        }
        return count;
    }

    private double runFuzzyInference(double ecart, double progression, double tendance) {
        try {
            if (fis != null) {
                fis.setVariable("ecart", ecart);
                fis.setVariable("progression", progression);
                fis.setVariable("tendance", tendance);
                fis.evaluate();
                double rate = fis.getVariable("concessionRate").getValue();
                return (Double.isNaN(rate) || rate < 0) ? fallbackRate(ecart, progression) : rate;
            }
            return fallbackRate(ecart, progression);
        } catch (Exception e) {
            return fallbackRate(ecart, progression);
        }
    }

    private double fallbackRate(double ecart, double progression) {
        double rate;
        if      (ecart > 45) rate = 0.02;
        else if (ecart > 30) rate = 0.06;
        else if (ecart > 15) rate = 0.18;
        else if (ecart > 5)  rate = 0.32;
        else                 rate = 0.45;
        if (progression > 0.7) rate = Math.min(0.5, rate + 0.1);
        return rate;
    }

    private double computeTrend(List<Number> historique, double prixActuel) {
        if (historique == null || historique.size() < 2) return 0.0;
        double last       = historique.get(historique.size() - 1).doubleValue();
        double secondLast = historique.get(historique.size() - 2).doubleValue();
        return Math.max(-1.0, Math.min(1.0, (last - secondLast) / prixActuel));
    }

    private String deriveTrend(double tendance) {
        if (tendance > 0.01)  return "IMPROVING";
        if (tendance < -0.01) return "DECLINING";
        return "STABLE";
    }

    private String deriveBehavior(double ecart) {
        if (ecart > 30)  return "AGGRESSIVE";
        if (ecart >= 10) return "SERIOUS";
        return "CLOSE";
    }

    private Map<String, Object> runKimiSellerInference(double current, double plancher, double offer, int round, int max, List<Number> history) {
        try {
            String systemPrompt = "Tu es un vendeur expert et coriace sur AuraMarket. Ta mission est de maximiser le profit. Ne sois pas trop facile.";
            String userPrompt = String.format(
                "Négociation en cours: \n" +
                "- Prix catalogue (départ): %.2f MAD \n" +
                "- Ton prix plancher (SECRET, ne jamais descendre en dessous): %.2f MAD \n" +
                "- Offre actuelle de l'acheteur: %.2f MAD \n" +
                "- Round: %d/%d \n" +
                "- Historique des offres de l'acheteur: %s \n\n" +
                "Directives stratégiques: \n" +
                "1. Ne propose JAMAIS ton prix plancher dès le début. \n" +
                "2. Si l'offre de l'acheteur est très basse (< 80%% de ton prix), reste très ferme (concession de 1%% max). \n" +
                "3. Si l'acheteur augmente ses offres, fais des petits pas (concessions de 2-5%%). \n" +
                "4. Ton but est de finir le plus haut possible au-dessus de %.2f MAD. \n" +
                "5. Si l'offre dépasse ton prix actuel, accepte immédiatement.\n" +
                "Réponds UNIQUEMENT au format JSON: {\"nouveauPrix\": double, \"isFinalOffer\": boolean}",
                current, plancher, offer, round, max, (history != null ? history.toString() : "Aucun"), plancher
            );

            String response = kimi.askKimi(systemPrompt, userPrompt, "NEGO");
            // Simple JSON extraction
            int start = response.indexOf("{");
            int end = response.lastIndexOf("}");
            if (start != -1 && end != -1) {
                String json = response.substring(start, end + 1);
                return mapper.readValue(json, Map.class);
            }
        } catch (Exception e) {
            System.err.println("[Kimi Seller Error] " + e.getMessage());
        }
        return null;
    }

    private double round2(double val) { return Math.round(val * 100.0) / 100.0; }
    private double toDouble(Object o) { 
        if (o instanceof String) return Double.parseDouble((String) o);
        return ((Number) o).doubleValue(); 
    }
    private int    toInt(Object o)    { return ((Number) o).intValue(); }

    private Map<String, Object> build(String id, double nouveauPrix, double concession,
                                       String behavior, String trend,
                                       int round, boolean finalOffer) {
        Map<String, Object> res = new HashMap<>();
        res.put("negociationId", id);
        res.put("nouveauPrix",   round2(nouveauPrix));
        res.put("concession",    round2(concession));
        res.put("buyerBehavior", behavior);
        res.put("buyerTrend",    trend);
        res.put("roundActuel",   round);
        res.put("isFinalOffer",  finalOffer);
        return res;
    }
}