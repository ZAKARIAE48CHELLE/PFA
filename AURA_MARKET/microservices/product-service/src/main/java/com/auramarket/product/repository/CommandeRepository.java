package com.auramarket.product.repository;

import com.auramarket.product.entity.Commande;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.UUID;

public interface CommandeRepository extends JpaRepository<Commande, UUID> {
    List<Commande> findByAcheteurId(UUID acheteurId);
    List<Commande> findByVendeurId(UUID vendeurId);
}
