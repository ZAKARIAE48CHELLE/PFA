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
 *
 * RÈGLES ABSOLUES :
 *   1. nouveauPrix >= prixMin
 *   2. nouveauPrix >= prixPropose
 *   3. nouveauPrix <= prixActuel
 *   4. prixPropose ~= prixMin → accepter
 *   5. prixPropose < prixMin  → contre-proposer prixMin
 *   6. roundActuel >= roundsMax → offre finale = prixMin
 *
 * NOUVEAUTÉS vs version précédente :
 *   - computeReinforcementBonus() : score comportemental acheteur
 *     → acheteur coopératif (monte ses offres) = bonus concession
 *     → acheteur manipulateur (baisse ses offres) = malus concession
 *   - computeStagnationBonus() : détecte si l'acheteur est bloqué
 *     → 3+ offres identiques = bonus progressif pour débloquer
 *   - concessionRate clampé [0.01, 0.5] → agent bouge TOUJOURS minimum
 *
 * RESPONSABILITÉ DU BRIDGE/CALLER :
 *   - Passer le nouveauPrix du round N comme prixActuel du round N+1
 *   - Ajouter prixPropose à historiqueOffres avant chaque appel
 *   - Ne jamais appeler si isFinalOffer == true
 *   - Ne jamais appeler si roundActuel > roundsMax
 */
public class AgentNegociation extends Agent {

    private final ObjectMapper mapper = new ObjectMapper();
    private FIS fis;

    @Override
    protected void setup() {
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

    // =========================================================================
    // FUZZY ENGINE
    // =========================================================================

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

    // =========================================================================
    // CORE LOGIC
    // =========================================================================

    @SuppressWarnings("unchecked")
    private Map<String, Object> processNegotiation(Map<String, Object> input) {

        String negociationId    = (String) input.get("negociationId");
        double prixActuel       = toDouble(input.get("prixActuel"));
        double prixMin          = toDouble(input.get("prixMin"));
        double prixPropose      = toDouble(input.get("prixPropose"));
        int    roundActuel      = toInt(input.get("roundActuel"));
        int    roundsMax        = toInt(input.get("roundsMax"));
        List<Number> historique = (List<Number>) input.get("historiqueOffres");

        System.out.println("\n[AgentNegociation] ══════════════════════════════════");
        System.out.println("[AgentNegociation] Round " + roundActuel + "/" + roundsMax);
        System.out.println("[AgentNegociation] prixActuel=" + prixActuel
                + " | prixMin=" + prixMin + " | prixPropose=" + prixPropose);

        // ── GARDE 0 : Config invalide ─────────────────────────────────────────
        if (prixMin >= prixActuel) {
            System.err.println("[GUARD 0] prixMin >= prixActuel — config invalide");
            return build(negociationId, prixActuel, 0, "INVALID_CONFIG", "STABLE", roundActuel, true);
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
        double epsilon = 0.05;
        if (prixPropose < prixMin - epsilon) {
            System.out.println("[GUARD 3] Sous plancher → contre-proposition prixMin=" + prixMin);
            return build(negociationId, prixMin, prixActuel - prixMin, "AGGRESSIVE", "DECLINING", roundActuel, false);
        }

        // ── GARDE 4 : Au plancher (avec epsilon) ──────────────────────────────
        if (prixPropose <= prixMin + epsilon) {
            System.out.println("[GUARD 4] Au plancher → acceptation immédiate");
            return build(negociationId, prixMin, prixActuel - prixMin, "ACCEPTED_AT_FLOOR", "IMPROVING", roundActuel, true);
        }

        // ── GARDE 4b : Marge résiduelle nulle ────────────────────────────────
        if (prixActuel - prixMin <= epsilon) {
            System.out.println("[GUARD 4b] Marge résiduelle nulle → clôture");
            return build(negociationId, prixMin, 0, "FLOOR_REACHED", "STABLE", roundActuel, true);
        }

        // ── GARDE 5 : Acheteur au-dessus du prix actuel ──────────────────────
        if (prixPropose >= prixActuel) {
            System.out.println("[GUARD 5] prixPropose >= prixActuel → acceptation");
            return build(negociationId, prixPropose, 0, "ACCEPTED", "IMPROVING", roundActuel, true);
        }

        // ── GARDE 6 : Dernier round ───────────────────────────────────────────
        if (roundActuel >= roundsMax) {
            System.out.println("[GUARD 6] Dernier round → offre finale prixMin=" + prixMin);
            String beh = deriveBehavior((prixActuel - prixPropose) / prixActuel * 100.0);
            return build(negociationId, prixMin, prixActuel - prixMin, beh, "FINAL", roundActuel, true);
        }

        // ── ÉTAPE 1 : Variables fuzzy ─────────────────────────────────────────
        double ecart       = (prixActuel - prixPropose) / prixActuel * 100.0;
        double progression = (double) roundActuel / roundsMax;
        double tendance    = computeTrend(historique, prixActuel);

        String buyerBehavior = deriveBehavior(ecart);
        String buyerTrend    = deriveTrend(tendance);

        System.out.println("[FUZZY INPUT] ecart=" + round2(ecart)
                + "% | progression=" + round2(progression)
                + " | tendance=" + round2(tendance)
                + " | behavior=" + buyerBehavior);

        // ── ÉTAPE 2 : Fuzzy inference ─────────────────────────────────────────
        double concessionRate = runFuzzyInference(ecart, progression, tendance);

        // ── ÉTAPE 3 : Renforcement comportemental ─────────────────────────────
        // Score basé sur l'historique COMPLET des offres de l'acheteur.
        // Récompense les acheteurs qui montent leurs offres (coopératifs).
        // Punit les acheteurs qui baissent ou restent stagnants (manipulateurs).
        //
        // Calcul:
        //   Pour chaque paire consécutive dans historiqueOffres:
        //     delta = offre[i] - offre[i-1]
        //     si delta > 0  : acheteur monte    → +0.05 par palier
        //     si delta == 0 : acheteur stagne   → -0.02 par palier
        //     si delta < 0  : acheteur descend  → -0.04 par palier
        //   Score final normalisé entre -0.15 et +0.15
        double reinforcementBonus = computeReinforcementBonus(historique, prixActuel);
        System.out.println("[REINFORCEMENT] bonus=" + round2(reinforcementBonus));

        // ── ÉTAPE 4 : Stagnation bonus ────────────────────────────────────────
        // Si l'acheteur répète le même prix 3+ fois → il est bloqué.
        // On lui fait une concession supplémentaire pour débloquer la situation.
        //
        // Calcul:
        //   Compter combien de fois la dernière offre est répétée dans historique.
        //   repetitions >= 3 → bonus = (repetitions - 2) * 0.05
        //   Plafonné à +0.20 pour éviter de trop concéder d'un coup.
        double stagnationBonus = computeStagnationBonus(historique);
        if (stagnationBonus > 0) {
            System.out.println("[STAGNATION] " + countRepetitions(historique)
                    + " répétitions détectées → bonus=" + round2(stagnationBonus));
        }

        // Taux final = fuzzy + renforcement + stagnation
        // Clampé [0.01, 0.5] → agent bouge TOUJOURS au minimum 1% de la marge
        concessionRate = Math.max(0.01, Math.min(0.5,
                concessionRate + reinforcementBonus + stagnationBonus));
        System.out.println("[FINAL RATE] concessionRate=" + round2(concessionRate));

        // ── ÉTAPE 5 : Calcul concession ───────────────────────────────────────
        double marge      = prixActuel - prixMin;
        double concession = concessionRate * marge;
        double candidat   = prixActuel - concession;

        System.out.println("[CALC] marge=" + round2(marge)
                + " | concession=" + round2(concession)
                + " | candidat=" + round2(candidat));

        // ── ÉTAPE 6 : Protection vendeur ─────────────────────────────────────
        // Si candidat descend sous l'offre acheteur → rencontrer à mi-chemin
        if (candidat <= prixPropose) {
            System.out.println("[SELLER PROTECTION] candidat sous prixPropose → mi-chemin");
            candidat = (prixActuel + prixPropose) / 2.0;
        }

        // ── ÉTAPE 7 : Clamp absolu ────────────────────────────────────────────
        double nouveauPrix = candidat;
        nouveauPrix = Math.max(prixMin, nouveauPrix);      // jamais sous prixMin
        nouveauPrix = Math.max(prixPropose, nouveauPrix);  // jamais sous prixPropose
        nouveauPrix = Math.min(prixActuel, nouveauPrix);   // jamais au-dessus prixActuel

        System.out.println("[CLAMP] " + round2(candidat) + " → " + round2(nouveauPrix));

        // ── ÉTAPE 8 : Détection blocage ───────────────────────────────────────
        boolean isFinalOffer = (nouveauPrix >= prixActuel);
        if (isFinalOffer) System.out.println("[BLOCKED] Agent bloqué → clôture forcée");

        System.out.println("[RESULT] nouveauPrix=" + round2(nouveauPrix)
                + " isFinalOffer=" + isFinalOffer);
        System.out.println("[AgentNegociation] ══════════════════════════════════\n");

        return build(negociationId, nouveauPrix, prixActuel - nouveauPrix,
                buyerBehavior, buyerTrend, roundActuel, isFinalOffer);
    }

    // =========================================================================
    // REINFORCEMENT : score comportemental acheteur
    // =========================================================================

    /**
     * Analyse l'historique complet des offres acheteur.
     * Retourne un bonus entre -0.15 et +0.15 à ajouter au concessionRate.
     *
     * Logique :
     *   - Chaque offre montante  (+) → récompense  : +0.05
     *   - Chaque offre stagnante (=) → neutre/malus : -0.02
     *   - Chaque offre baissante (-) → punition     : -0.04
     */
    private double computeReinforcementBonus(List<Number> historique, double prixActuel) {
        if (historique == null || historique.size() < 2) return 0.0;

        double score = 0.0;
        for (int i = 1; i < historique.size(); i++) {
            double prev = historique.get(i - 1).doubleValue();
            double curr = historique.get(i).doubleValue();
            double delta = curr - prev;

            if (delta > prixActuel * 0.001) {
                score += 0.05;  // acheteur monte → coopératif → récompense
            } else if (Math.abs(delta) <= prixActuel * 0.001) {
                score -= 0.02;  // acheteur stagne → léger malus
            } else {
                score -= 0.04;  // acheteur baisse → manipulateur → punition
            }
        }

        // Normaliser entre -0.15 et +0.15
        return Math.max(-0.15, Math.min(0.15, score));
    }

    /**
     * Détecte la stagnation : acheteur qui répète le même prix.
     * Retourne un bonus entre 0 et 0.20.
     *
     * Logique :
     *   - 3 répétitions → +0.05
     *   - 4 répétitions → +0.10
     *   - 5+ répétitions → +0.15 (plafonné à +0.20)
     */
    private double computeStagnationBonus(List<Number> historique) {
        int repetitions = countRepetitions(historique);
        if (repetitions < 3) return 0.0;
        return Math.min(0.20, (repetitions - 2) * 0.05);
    }

    /**
     * Compte combien de fois la dernière offre est répétée en fin d'historique.
     */
    private int countRepetitions(List<Number> historique) {
        if (historique == null || historique.size() < 2) return 0;
        double lastOffer = historique.get(historique.size() - 1).doubleValue();
        int count = 1;
        for (int i = historique.size() - 2; i >= 0; i--) {
            if (Math.abs(historique.get(i).doubleValue() - lastOffer) < 0.01) {
                count++;
            } else {
                break;
            }
        }
        return count;
    }

    // =========================================================================
    // FUZZY INFERENCE
    // =========================================================================

    private double runFuzzyInference(double ecart, double progression, double tendance) {
        try {
            if (fis != null) {
                fis.setVariable("ecart", ecart);
                fis.setVariable("progression", progression);
                fis.setVariable("tendance", tendance);
                fis.evaluate();

                double rate = fis.getVariable("concessionRate").getValue();
                if (Double.isNaN(rate) || rate < 0) {
                    System.err.println("[FUZZY FALLBACK] valeur invalide : " + rate);
                    return fallbackRate(ecart, progression);
                }
                return rate;
            } else {
                System.err.println("[FUZZY FALLBACK] FIS non chargé");
                return fallbackRate(ecart, progression);
            }
        } catch (Exception e) {
            System.err.println("[FUZZY ERROR] " + e.getMessage());
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
        System.out.println("[FALLBACK] ecart=" + round2(ecart) + " → rate=" + rate);
        return rate;
    }

    // =========================================================================
    // HELPERS
    // =========================================================================

    private double computeTrend(List<Number> historique, double prixActuel) {
        if (historique == null || historique.size() < 2) return 0.0;
        double last       = historique.get(historique.size() - 1).doubleValue();
        double secondLast = historique.get(historique.size() - 2).doubleValue();
        return Math.max(-1.0, Math.min(1.0, (last - secondLast) / prixActuel));
    }

    private String deriveBehavior(double ecart) {
        if (ecart > 30)  return "AGGRESSIVE";
        if (ecart >= 10) return "SERIOUS";
        return "CLOSE";
    }

    private String deriveTrend(double tendance) {
        if (tendance > 0.05)  return "IMPROVING";
        if (tendance < -0.05) return "DECLINING";
        return "STABLE";
    }

    private double round2(double val) {
        return Math.round(val * 100.0) / 100.0;
    }

    private double toDouble(Object o) { return ((Number) o).doubleValue(); }
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