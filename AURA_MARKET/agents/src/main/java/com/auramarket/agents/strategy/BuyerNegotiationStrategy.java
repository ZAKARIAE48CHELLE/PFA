package com.auramarket.agents.strategy;

public class BuyerNegotiationStrategy {

    /**
     * Deterministic buyer negotiation offer formula.
     * - Round 1: offer = prixActuel * 0.72
     * - Round 2+: increase previous offer based on Trend
     * - Clamp with prixCible. Never exceed prixCible.
     */
    public static double calculateNextOffer(double prixCible, double prixActuel, String buyerTrend, int round, double derniereOffre) {
        double offre;

        if (round <= 1) {
            offre = prixActuel * 0.72;
        } else {
            double mult = switch (buyerTrend != null ? buyerTrend.toUpperCase() : "STABLE") {
                case "DECLINING"  -> 1.03;
                case "IMPROVING"  -> 1.07;
                default           -> 1.05; // STABLE
            };
            offre = derniereOffre * mult;
        }

        // Final absolute clamping
        double clampedOffre = Math.min(offre, prixCible);
        return round2(clampedOffre);
    }

    private static double round2(double val) {
        return Math.round(val * 100.0) / 100.0;
    }
}
