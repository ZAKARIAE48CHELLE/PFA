package com.auramarket.product.repository;

import com.auramarket.product.entity.Paiement;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;

public interface PaiementRepository extends JpaRepository<Paiement, UUID> {
}
