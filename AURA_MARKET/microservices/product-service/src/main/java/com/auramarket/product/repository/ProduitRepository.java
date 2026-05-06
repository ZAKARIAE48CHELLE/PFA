package com.auramarket.product.repository;

import com.auramarket.product.entity.Produit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import org.springframework.data.jpa.repository.Query;
import org.springframework.data.domain.Pageable;
import java.util.List;
import java.util.UUID;

@Repository
public interface ProduitRepository extends JpaRepository<Produit, UUID> {
    List<Produit> findByCategorie(String categorie, Pageable pageable);

    @Query("SELECT p.categorie, COUNT(p) FROM Produit p GROUP BY p.categorie")
    List<Object[]> countProductsByCategory();
}
