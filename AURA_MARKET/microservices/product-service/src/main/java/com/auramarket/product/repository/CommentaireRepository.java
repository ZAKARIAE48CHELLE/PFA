package com.auramarket.product.repository;

import com.auramarket.product.entity.Commentaire;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.UUID;

public interface CommentaireRepository extends JpaRepository<Commentaire, UUID> {
    List<Commentaire> findByProduitIdOrderByDatePublicationDesc(UUID produitId);
}
