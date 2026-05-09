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
        double prixMin          = toDouble(input.get("prixMin"));
        double prixPropose      = toDouble(input.get("prixPropose"));
        int    roundActuel      = toInt(input.get("roundActuel"));
        int    roundsMax        = toInt(input.get("roundsMax"));
        List<Number> historique = (List<Number>) input.get("historiqueOffres");
        double epsilon = 0.05;

        System.out.println("\n[AgentNegociation] ══════════════════════════════════");
        System.out.println("[AgentNegociation] Round " + roundActuel + "/" + roundsMax);
        System.out.println("[AgentNegociation] prixActuel=" + prixActuel
                + " | prixMin=" + prixMin + " | prixPropose=" + prixPropose);

        // ── GARDE 0 : Config invalide ─────────────────────────────────────────
        if (prixMin <= 0 || prixMin > prixActuel + epsilon) {
            System.err.println("[GUARD 0b] prixMin invalide : " + prixMin + " (prixActuel=" + prixActuel + ")");
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
            return build(negociationId, prixMin, prixActuel - prixMin, "TIMEOUT", "STABLE", roundActuel, true);
        }

        // ── GARDE 2 : Offre invalide ──────────────────────────────────────────
        if (prixPropose <= 0) {
            System.err.println("[GUARD 2] prixPropose invalide : " + prixPropose);
            return build(negociationId, prixActuel, 0, "INVALID", "STABLE", roundActuel, false);
        }

        // ── GARDE 3 : Sous le plancher ────────────────────────────────────────
        if (prixPropose < prixMin - epsilon) {
            System.out.println("[GUARD 3] Offre sous plancher → vendeur immobile");
            return build(negociationId, prixActuel, 0,
                         "AGGRESSIVE_BUYER", "DECLINING", roundActuel, false);
            // isFinalOffer = false → laisse l'acheteur faire une meilleure offre
        }

        // ── GARDE 4 : Au plancher (avec epsilon) ──────────────────────────────
        if (prixPropose <= prixMin + epsilon) {
            System.out.println("[GUARD 4] Au plancher → acceptation immédiate");
            return build(negociationId, prixMin, prixActuel - prixMin, "ACCEPTED_AT_FLOOR", "IMPROVING", roundActuel, true);
        }

        // ── GARDE 4b : Marge résiduelle nulle ────────────────────────────────
        if (prixActuel - prixMin <= epsilon) {
            System.out.println("[GUARD 4b] Marge résiduelle nulle → attente acheteur sur prixMin=" + prixMin);
            return build(negociationId, prixMin, 0, "FLOOR_REACHED", "STABLE", roundActuel, (roundActuel >= roundsMax));
        }


        // ── ÉTAPE 0 : Kimi Inference (Si disponible) ─────────────────────────
        if (kimi != null) {
            Map<String, Object> kimiResult = runKimiSellerInference(prixActuel, prixMin, prixPropose, roundActuel, roundsMax, historique);
            if (kimiResult != null) {
                double nuevo = toDouble(kimiResult.get("nouveauPrix"));
                
                // Security: NEVER go below prixMin even if AI is crazy
                nuevo = Math.max(prixMin, nuevo);
                // Security: NEVER go below what the buyer just offered (don't give it cheaper than they asked!)
                nuevo = Math.max(prixPropose, nuevo);
                // Security: Don't go above current price (unless it's an acceptance of a higher bid)
                if (prixPropose < prixActuel) {
                    nuevo = Math.min(prixActuel, nuevo);
                }

                boolean isFinal = (boolean) kimiResult.getOrDefault("isFinalOffer", false) || (roundActuel >= roundsMax);
                
                System.out.println("[AgentNegociation] Kimi a décidé : " + nuevo);
                return build(negociationId, nuevo, prixActuel - nuevo, "AI_STRATEGY", "AI_TREND", roundActuel, isFinal);
            }
        }

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
        concessionRate = Math.max(0.12, concessionRate);
        
        // Bonus si acheteur serieux
        if ("IMPROVING".equalsIgnoreCase(buyerTrend)) {
            concessionRate += 0.08;
        }

        // Limiter la concession maximum par round (ex: 25% de la marge pour ne pas descendre trop vite d'un coup)
        double maxConcessionParRound = 0.25;
        concessionRate = Math.max(0.12, Math.min(maxConcessionParRound, concessionRate));

        // ── ÉTAPE 5 : Calcul concession ───────────────────────────────────────
        double marge      = prixActuel - prixMin;
        double concession = concessionRate * marge;
        double candidat   = prixActuel - concession;
        
        // Si c'est l'avant dernier ou dernier round, on s'approche agressivement du min
        if (roundActuel >= roundsMax - 1) {
            candidat = prixMin + (marge * 0.1); // Propose presque le min (10% de la marge au-dessus)
        }

        // ── ÉTAPE 6 : Protection vendeur (Stubbornness) ───────────────────────
        if (candidat <= prixPropose) {
            // Le vendeur ne concède que 25% de l'écart au lieu de 50%
            candidat = prixActuel - (prixActuel - prixPropose) * 0.25;
            candidat = Math.max(prixMin, candidat);
        }
        
        System.out.println("[DEBUG] concessionRate=" + concessionRate + " | marge=" + marge + " | candidat=" + candidat);

        // ── SEUIL DE CONVERGENCE AUTOMATIQUE ──────────────────────────────────
        double margeInitiale = prixActuel - prixMin;
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

        // Si l'écart absolu est < 10 MAD et prixPropose > prixMin → accepter
        if (ecartRestant > 0 && ecartRestant < 10.0 && prixPropose > prixMin) {
            System.out.println("[CONVERGENCE] Écart absolu " 
                + round2(ecartRestant) + " MAD < 10 MAD → acceptation");
            return build(negociationId, prixPropose, prixActuel - prixPropose,
                         "ACCEPTED", "IMPROVING", roundActuel, true);
        }

        // ── ÉTAPE 7 : Clamp absolu ────────────────────────────────────────────
        double nouveauPrix = candidat;
        nouveauPrix = Math.max(prixMin, nouveauPrix);
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

    private Map<String, Object> runKimiSellerInference(double current, double min, double offer, int round, int max, List<Number> history) {
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
                current, min, offer, round, max, (history != null ? history.toString() : "Aucun"), min
            );

            String response = kimi.askKimi(systemPrompt, userPrompt);
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