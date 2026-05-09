package com.auramarket.agents.strategy;

import java.util.List;

public class BuyerNegotiationStrategy {

    public static double calculateNextOffer(double prixCible, double currentSellerPrice, String sellerTrend, int round, List<Double> history, int maxRounds) {
        double nextOffer;

        if (round <= 1 || history.isEmpty()) {
            nextOffer = currentSellerPrice * 0.72;
        } else {
            double lastBuyerOffer = history.get(history.size() - 1);
            
            double incrementPercent = 0.05; // STABLE
            if ("DECLINING".equalsIgnoreCase(sellerTrend)) {
                incrementPercent = 0.03;
            } else if ("IMPROVING".equalsIgnoreCase(sellerTrend)) {
                incrementPercent = 0.07;
            }
            
            nextOffer = lastBuyerOffer * (1 + incrementPercent);
        }

        // Ne jamais envoyer exactement prixCible avant le dernier round
        if (round < maxRounds && nextOffer >= prixCible) {
            nextOffer = prixCible - 0.5; 
        }

        // Clamp final absolu
        nextOffer = Math.min(nextOffer, prixCible);

        return round2(nextOffer);
    }

    private static double round2(double val) {
        return Math.round(val * 100.0) / 100.0;
    }
}
